import React, { useEffect, useMemo, useState } from "react";
import { API } from "./auth-client";
import { WorkspaceHeader } from "./WorkspaceHeader";

type Expense = { id:number; name:string; amount:number|null; category:string; day_of_month:number };
type Person = { id?:number; name:string; email:string; phone:string; share_amount:number; is_paid?:boolean; paid_at?:string|null; last_reminded_at?:string|null };
type Split = { expense_id:number; expense_name:string; amount:number; participants:Person[] };

const money = (value:number) => `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits:2 })}`;

export function ExpenseSplits({ onLogout }:{ onLogout?:()=>void }) {
  const [monthDate,setMonthDate]=useState(new Date());
  const [expenses,setExpenses]=useState<Expense[]>([]);
  const [splits,setSplits]=useState<Record<number,Split>>({});
  const [selected,setSelected]=useState<Expense|null>(null);
  const [search,setSearch]=useState("");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const year=monthDate.getFullYear(), month=monthDate.getMonth()+1;

  const load=async()=>{
    setLoading(true); setError("");
    try {
      const response=await fetch(`${API}/api/expenses/${year}/${month}`);
      if(!response.ok) throw new Error("Unable to load expenses");
      const items:Expense[]=await response.json(); setExpenses(items);
      const pairs=await Promise.all(items.map(async item=>{
        const result=await fetch(`${API}/api/expense-splits/${item.id}`);
        return [item.id,result.ok ? await result.json() : {expense_id:item.id,expense_name:item.name,amount:item.amount||0,participants:[]}] as const;
      }));
      setSplits(Object.fromEntries(pairs));
    } catch(e){setError(e instanceof Error?e.message:"Unable to load split expenses");}
    finally{setLoading(false);}
  };
  useEffect(()=>{void load();},[year,month]);

  const visible=useMemo(()=>expenses.filter(item=>`${item.name} ${item.category}`.toLowerCase().includes(search.toLowerCase())),[expenses,search]);
  const active=Object.values(splits).filter(item=>item.participants.length>0);
  const outstanding=active.reduce((sum,item)=>sum+item.participants.filter(person=>!person.is_paid).reduce((subtotal,person)=>subtotal+Number(person.share_amount),0),0);
  const moveMonth=(delta:number)=>setMonthDate(current=>new Date(current.getFullYear(),current.getMonth()+delta,1));

  return <main className="split-workspace">
    <WorkspaceHeader section="Split expenses" onLogout={onLogout}/>
    <div className="split-shell">
      <section className="split-hero">
        <div><span className="split-kicker">SHARED MONEY, MADE SIMPLE</span><h1>Split expenses.<br/>Keep friendships easy.</h1><p>Divide any bill, track who has paid, and send a friendly reminder by email or phone.</p></div>
        <div className="split-summary"><span>OUTSTANDING TO COLLECT</span><strong>{money(outstanding)}</strong><small>{active.length} active split{active.length===1?"":"s"}</small></div>
      </section>

      <section className="split-toolbar">
        <button onClick={()=>moveMonth(-1)} aria-label="Previous month"><i className="fas fa-chevron-left"/></button>
        <div><span>SELECTED MONTH</span><strong>{monthDate.toLocaleDateString("en-IN",{month:"long",year:"numeric"})}</strong></div>
        <button onClick={()=>moveMonth(1)} aria-label="Next month"><i className="fas fa-chevron-right"/></button>
      </section>

      <section className="split-panel">
        <div className="split-panel-head"><div><span>YOUR EXPENSES</span><h2>Choose a bill to split</h2></div><label><i className="fas fa-search"/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search expenses" aria-label="Search expenses"/></label></div>
        {loading?<div className="split-state"><i className="fas fa-circle-notch fa-spin"/> Loading your expenses…</div>:error?<div className="split-state error">{error}<button onClick={load}>Try again</button></div>:visible.length===0?<div className="split-state"><i className="fas fa-receipt"/> Add an expense first, then return here to split it.</div>:
        <div className="split-grid">{visible.map(expense=>{
          const people=splits[expense.id]?.participants||[];
          const paid=people.filter(item=>item.is_paid).length;
          return <article key={expense.id} className={people.length?"configured":""}>
            <div className="split-card-icon"><i className={`fas ${people.length?"fa-user-group":"fa-receipt"}`}/></div>
            <div className="split-card-copy"><span>{expense.category||"Expense"} · due {expense.day_of_month}</span><h3>{expense.name}</h3><strong>{expense.amount==null?"Amount not set":money(expense.amount)}</strong></div>
            <div className="split-card-status">{people.length?<><b>{paid}/{people.length} paid</b><small>{money(people.filter(p=>!p.is_paid).reduce((sum,p)=>sum+Number(p.share_amount),0))} pending</small></>:<><b>Not split</b><small>Add people and shares</small></>}</div>
            <button onClick={()=>setSelected(expense)}>{people.length?"Manage split":"Split this bill"}<i className="fas fa-arrow-right"/></button>
          </article>;
        })}</div>}
      </section>
    </div>
    {selected&&<SplitEditor expense={selected} existing={splits[selected.id]?.participants||[]} onClose={()=>setSelected(null)} onChanged={load}/>} 
  </main>;
}

function SplitEditor({expense,existing,onClose,onChanged}:{expense:Expense;existing:Person[];onClose:()=>void;onChanged:()=>Promise<void>}){
  const half=Number(((expense.amount||0)/2).toFixed(2));
  const [people,setPeople]=useState<Person[]>(existing.length?existing:[{name:"",email:"",phone:"",share_amount:half},{name:"",email:"",phone:"",share_amount:Number(((expense.amount||0)-half).toFixed(2))}]);
  const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false);
  const total=people.reduce((sum,item)=>sum+Number(item.share_amount||0),0);
  const update=(index:number,patch:Partial<Person>)=>setPeople(items=>items.map((item,i)=>i===index?{...item,...patch}:item));
  const save=async()=>{setBusy(true);setMessage("");try{const response=await fetch(`${API}/api/expense-splits/${expense.id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({participants:people})});const data=await response.json();if(!response.ok)throw new Error(data.detail||"Could not save split");setPeople(data.participants);setMessage("Split saved. Reminders are ready.");await onChanged();}catch(e){setMessage(e instanceof Error?e.message:"Could not save split");}finally{setBusy(false);}};
  const remind=async(person:Person)=>{if(!person.id)return setMessage("Save the split before sending reminders.");const channels=[person.email&&"email",person.phone&&"sms"].filter(Boolean);const response=await fetch(`${API}/api/expense-splits/${expense.id}/${person.id}/remind`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({channels})});const data=await response.json();if(!response.ok)return setMessage(data.detail||"Reminder failed");if(data.manual_sms)window.location.href=`sms:${data.manual_sms.phone}?&body=${encodeURIComponent(data.manual_sms.body)}`;setMessage(data.manual_sms?"Email sent where selected; Messages opened for the free SMS reminder.":"Reminder sent.");};
  const paid=async(person:Person)=>{if(!person.id)return;const next=!person.is_paid;const response=await fetch(`${API}/api/expense-splits/${expense.id}/${person.id}/paid?paid=${next}`,{method:"PATCH"});if(response.ok){setPeople(items=>items.map(item=>item.id===person.id?{...item,is_paid:next}:item));await onChanged();}};
  return <div className="split-drawer-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><section className="split-drawer" role="dialog" aria-modal="true" aria-label={`Split ${expense.name}`}>
    <header><div><span>SPLIT BILL</span><h2>{expense.name}</h2><p>{money(expense.amount||0)} bill · {money(total)} assigned</p></div><button onClick={onClose} aria-label="Close"><i className="fas fa-xmark"/></button></header>
    <div className="split-editor-help"><i className="fas fa-shield-heart"/><p><strong>Private and secure</strong><span>Add an email, phone number, or both. Phone reminders use your Messages app when free server SMS is unavailable.</span></p></div>
    <div className="split-editor-people">{people.map((person,index)=><article key={person.id||index}>
      <div className="split-person-number">{index+1}</div>
      <label>Name<input value={person.name} onChange={e=>update(index,{name:e.target.value})} placeholder="Friend or family"/></label>
      <label>Email<input type="email" value={person.email} onChange={e=>update(index,{email:e.target.value})} placeholder="Optional"/></label>
      <label>Phone<input type="tel" value={person.phone} onChange={e=>update(index,{phone:e.target.value})} placeholder="+91… (optional)"/></label>
      <label>Share amount<input type="number" min="0.01" step="0.01" value={person.share_amount} onChange={e=>update(index,{share_amount:Number(e.target.value)})}/></label>
      {person.id&&<div className="split-person-actions"><button className={person.is_paid?"paid":""} onClick={()=>paid(person)}><i className={`fas ${person.is_paid?"fa-circle-check":"fa-clock"}`}/>{person.is_paid?"Paid":"Mark paid"}</button><button disabled={person.is_paid} onClick={()=>remind(person)}><i className="fas fa-paper-plane"/>Remind</button></div>}
      {people.length>2&&<button className="split-person-remove" onClick={()=>setPeople(items=>items.filter((_,i)=>i!==index))} aria-label={`Remove ${person.name||`person ${index+1}`}`}><i className="fas fa-trash"/></button>}
    </article>)}</div>
    <button className="split-add-person" onClick={()=>setPeople(items=>[...items,{name:"",email:"",phone:"",share_amount:0}])}><i className="fas fa-plus"/>Add another person</button>
    {message&&<p className="split-feedback" role="status">{message}</p>}
    <footer><button onClick={onClose}>Cancel</button><button className="primary" onClick={save} disabled={busy||Math.abs(total-Number(expense.amount||0))>.01}>{busy?"Saving…":"Save split"}</button></footer>
  </section></div>;
}
