import React, { useEffect, useMemo, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";

const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;

interface PdfField {
  key: string; pdf_name: string; label: string; type: string; page: number;
  left: number; top: number; width: number; height: number; required: boolean; source: string;
}
interface PdfTemplateSummary {
  id: number; name: string; original_filename: string; page_count: number; analysis_mode: string;
  field_count: number; is_signed: boolean; warnings: string[]; created_at: string;
}
interface PdfTemplateDetail extends PdfTemplateSummary {
  fields: PdfField[]; suggestions: Record<string, string>; original_url: string;
  page_sizes: { width: number; height: number }[];
}

async function apiJson(url: string, options?: RequestInit) {
  const response = await fetch(`${API}${url}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "The PDF request could not be completed");
  return data;
}

export function PdfFormFiller({ onLogout }: { onLogout?: () => void }) {
  const [templates, setTemplates] = useState<PdfTemplateSummary[]>([]);
  const [selected, setSelected] = useState<PdfTemplateDetail | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [remember, setRemember] = useState<Record<string, boolean>>({});
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [layoutOpen, setLayoutOpen] = useState(false);

  const loadTemplates = async () => {
    const items = await apiJson("/api/pdf-forms");
    setTemplates(items);
  };
  useEffect(() => { loadTemplates().catch(error => setError(error.message)); }, []);

  const openTemplate = async (id: number) => {
    setBusy("opening"); setError(""); setNotice("");
    try {
      const detail: PdfTemplateDetail = await apiJson(`/api/pdf-forms/${id}`);
      setSelected(detail);
      setValues({ ...detail.suggestions });
      setRemember(Object.fromEntries(detail.fields.map(field => [field.key, true])));
    } catch (error: any) { setError(error.message); }
    finally { setBusy(""); }
  };

  const upload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return setError("Choose a PDF first");
    setBusy("uploading"); setError(""); setNotice("Analyzing fields and preserving the original PDF…");
    const form = new FormData(); form.append("file", file); form.append("name", name);
    try {
      const result = await apiJson("/api/pdf-forms/upload", { method: "POST", body: form });
      await loadTemplates();
      setSelected(result.template);
      setValues({ ...result.template.suggestions });
      setRemember(Object.fromEntries(result.template.fields.map((field: PdfField) => [field.key, true])));
      setNotice(result.reused ? "This PDF was already in your private library. Saved answers were restored." : `Analysis complete: ${result.template.fields.length} fields found.`);
      setFile(null); setName("");
    } catch (error: any) { setError(error.message); setNotice(""); }
    finally { setBusy(""); }
  };

  const updateField = (index: number, update: Partial<PdfField>) => {
    if (!selected) return;
    const fields = selected.fields.map((field, current) => current === index ? { ...field, ...update } : field);
    setSelected({ ...selected, fields, field_count: fields.length });
  };

  const addField = () => {
    if (!selected) return;
    const index = selected.fields.length + 1;
    setSelected({ ...selected, fields: [...selected.fields, {
      key: `manual_field_${index}`, pdf_name: "", label: `New field ${index}`, type: "text", page: 0,
      left: .35, top: .1, width: .5, height: .03, required: false, source: "manual",
    }] });
  };

  const saveLayout = async () => {
    if (!selected) return;
    setBusy("layout"); setError("");
    try {
      const detail = await apiJson(`/api/pdf-forms/${selected.id}/fields`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fields: selected.fields }),
      });
      setSelected(detail); setNotice("Field layout saved for future use."); setLayoutOpen(false);
      await loadTemplates();
    } catch (error: any) { setError(error.message); }
    finally { setBusy(""); }
  };

  const generate = async () => {
    if (!selected) return;
    setBusy("generating"); setError(""); setNotice("Generating and validating your PDF…");
    try {
      const result = await apiJson(`/api/pdf-forms/${selected.id}/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values, remember_keys: Object.keys(remember).filter(key => remember[key]) }),
      });
      setNotice(`Ready: ${result.filename}. The original PDF remains unchanged.`);
      const link = document.createElement("a"); link.href = `${API}${result.download_url}`; link.download = result.filename;
      document.body.appendChild(link); link.click(); link.remove();
    } catch (error: any) { setError(error.message); setNotice(""); }
    finally { setBusy(""); }
  };

  const completed = useMemo(() => selected ? selected.fields.filter(field => String(values[field.key] ?? "").trim()).length : 0, [selected, values]);

  return <div className="app-workspace pdf-workspace">
    <WorkspaceHeader section="PDF forms" onLogout={onLogout} />
    <main className="suite-content pdf-shell">
      <header className="suite-page-heading pdf-heading">
        <div><span className="suite-eyebrow">PRIVATE DOCUMENT WORKSPACE</span><h1>AI PDF Form Filler</h1><p>Upload once, review detected fields, and reuse your saved answers whenever the same information is requested.</p></div>
        <div className="pdf-trust"><i className="fas fa-shield-halved" /><span>Original preserved<br/><small>Values encrypted per user</small></span></div>
      </header>

      {error && <div className="pdf-alert error"><i className="fas fa-circle-exclamation" /> {error}</div>}
      {notice && <div className="pdf-alert success"><i className="fas fa-circle-check" /> {notice}</div>}

      <section className="pdf-upload-card">
        <div><span className="pdf-step">1</span><h2>Upload a form</h2><p>Fillable, text-based and scanned PDFs are supported. Maximum 20 MB.</p></div>
        <form onSubmit={upload}>
          <label className="pdf-dropzone">
            <i className="fas fa-file-pdf" />
            <strong>{file ? file.name : "Choose PDF"}</strong>
            <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "Tap to browse your device"}</span>
            <input type="file" accept="application/pdf,.pdf" onChange={event => setFile(event.target.files?.[0] || null)} />
          </label>
          <input aria-label="Document name" placeholder="Document name (optional)" value={name} onChange={event => setName(event.target.value)} />
          <button className="pdf-primary" disabled={!file || !!busy}><i className={`fas ${busy === "uploading" ? "fa-spinner fa-spin" : "fa-wand-magic-sparkles"}`} /> Analyze PDF</button>
        </form>
      </section>

      <div className="pdf-layout">
        <aside className="pdf-library">
          <div className="pdf-panel-title"><div><span className="pdf-step">2</span><h2>Your PDF library</h2></div><small>{templates.length} saved</small></div>
          {templates.length === 0 && <div className="pdf-empty"><i className="far fa-folder-open"/><p>Your uploaded forms will appear here.</p></div>}
          {templates.map(item => <button key={item.id} className={`pdf-template ${selected?.id === item.id ? "active" : ""}`} onClick={() => openTemplate(item.id)}>
            <i className="fas fa-file-lines"/><span><strong>{item.name}</strong><small>{item.field_count} fields · {item.page_count} page{item.page_count === 1 ? "" : "s"}</small></span><i className="fas fa-chevron-right"/>
          </button>)}
        </aside>

        <section className="pdf-editor">
          {!selected ? <div className="pdf-empty large"><i className="fas fa-arrow-left"/><h2>Select or upload a PDF</h2><p>The app will ask only for detected values it does not already remember.</p></div> : <>
            <div className="pdf-editor-head">
              <div><span className="pdf-step">3</span><h2>{selected.name}</h2><p>{selected.analysis_mode.toUpperCase()} analysis · {completed}/{selected.fields.length} completed</p></div>
              <div><a href={`${API}${selected.original_url}`} target="_blank" rel="noreferrer"><i className="fas fa-eye"/> Original</a><button onClick={() => setLayoutOpen(!layoutOpen)}><i className="fas fa-sliders"/> Review layout</button></div>
            </div>
            {selected.is_signed && <div className="pdf-alert error">This PDF is digitally signed. Generation is blocked to protect its signature.</div>}
            {selected.warnings?.map(warning => <div className="pdf-alert warning" key={warning}><i className="fas fa-triangle-exclamation"/> {warning}</div>)}

            {layoutOpen && <div className="pdf-layout-editor">
              <div className="pdf-layout-note"><strong>Field placement review</strong><span>Coordinates are percentages of the page. Use this only when OCR misses or misplaces a field.</span></div>
              {selected.fields.map((field, index) => <div className="pdf-layout-row" key={`${field.key}-${index}`}>
                <input value={field.label} aria-label={`Field ${index + 1} label`} onChange={event => updateField(index, { label: event.target.value, key: event.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || field.key })}/>
                <label>Page<input type="number" min="1" max={selected.page_count} value={field.page + 1} onChange={event => updateField(index, { page: Math.max(0, Number(event.target.value) - 1) })}/></label>
                {(["left", "top", "width"] as const).map(key => <label key={key}>{key}<input type="number" min="0" max="100" step="1" value={Math.round(field[key] * 100)} onChange={event => updateField(index, { [key]: Number(event.target.value) / 100 })}/></label>)}
                <button aria-label={`Remove ${field.label}`} onClick={() => setSelected({ ...selected, fields: selected.fields.filter((_, current) => current !== index) })}><i className="fas fa-trash"/></button>
              </div>)}
              <div className="pdf-layout-actions"><button onClick={addField}><i className="fas fa-plus"/> Add field</button><button className="pdf-primary" onClick={saveLayout} disabled={busy === "layout"}>Save layout</button></div>
            </div>}

            <div className="pdf-fields">
              {selected.fields.length === 0 && <div className="pdf-empty"><p>No fields detected. Open <b>Review layout</b> to add them.</p></div>}
              {selected.fields.map(field => <div className="pdf-field" key={field.key}>
                <label><span>{field.label}{field.required && <b>*</b>}</span><small>Page {field.page + 1} · {field.source === "acroform" ? "fillable field" : field.source.toUpperCase()}</small></label>
                {field.type === "checkbox" ? <input type="checkbox" checked={Boolean(values[field.key])} onChange={event => setValues({ ...values, [field.key]: event.target.checked })}/> :
                  <input type={field.type === "email" ? "email" : field.type === "date" ? "date" : "text"} value={String(values[field.key] ?? "")} onChange={event => setValues({ ...values, [field.key]: event.target.value })} placeholder={`Enter ${field.label.toLowerCase()}`}/>} 
                <label className="pdf-remember"><input type="checkbox" checked={remember[field.key] ?? true} onChange={event => setRemember({ ...remember, [field.key]: event.target.checked })}/><span>Remember securely</span></label>
              </div>)}
            </div>
            <div className="pdf-generate-bar"><div><strong>Original-quality output</strong><span>The source PDF is never overwritten; only a new filled copy is created.</span></div><button className="pdf-primary" disabled={!!busy || selected.is_signed || !selected.fields.length} onClick={generate}><i className={`fas ${busy === "generating" ? "fa-spinner fa-spin" : "fa-download"}`}/> Generate PDF</button></div>
          </>}
        </section>
      </div>
    </main>
  </div>;
}
