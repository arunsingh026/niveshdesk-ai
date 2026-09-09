# 📱 Access from iPhone & Mobile Devices

Your Monthly Expenses Tracker now works with **any IP address** - no need to update code when your IP changes!

## ✅ Problem Solved: Dynamic IP Support

**Before:** Had to update code every time your IP changed  
**After:** Works automatically with any IP!

---

## 🚀 Quick Start - Access from iPhone

### **Step 1: Find Your Computer's Current IP**

#### **Windows (Simple):**
```bash
ipconfig | findstr IPv4
```

Look for something like: `192.168.1.214`

#### **Mac:**
```bash
ipconfig getifaddr en0
```

#### **Linux:**
```bash
hostname -I | awk '{print $1}'
```

### **Step 2: Open on iPhone**

1. **Open Safari** on your iPhone
2. **Visit:** `http://YOUR_IP:5173`  
   Example: `http://192.168.1.214:5173`
3. **Sign in** with your email or mobile number and password
4. **Tap "Monthly Expenses"**

### **Step 3: Add to Home Screen (Optional but Recommended!)**

1. Tap the **Share** button (square with arrow up)
2. Scroll and tap **"Add to Home Screen"**
3. Name it: **"My Expenses"**
4. Tap **"Add"**
5. **Done!** You now have an app icon 🎉

---

## 🔄 When Your IP Changes

**Good News:** No code changes needed!

### **What to Do:**

1. **Find your new IP** (use command above)
2. **Use new IP in Safari:** `http://NEW_IP:5173`
3. **That's it!** Everything works automatically

### **Why It Works:**

✅ **Smart Frontend** - Automatically detects which IP you're using  
✅ **Dynamic Backend** - Accepts requests from any local network IP  
✅ **Zero Configuration** - No hardcoded IPs in the code  

---

## 📋 Checklist - First Time Setup

- [ ] Make sure computer and iPhone are on **same WiFi network**
- [ ] Find your computer's IP address
- [ ] Open Safari on iPhone (not Chrome!)
- [ ] Visit `http://YOUR_IP:5173`
- [ ] Register or sign in to your private account
- [ ] Test that "Server Running" shows green checkmark
- [ ] Test Monthly Expenses page loads
- [ ] Add to home screen for easy access

---

## 🛠️ Troubleshooting

### **❌ "Server Stopped" on iPhone**

**Causes:**
1. Computer and iPhone on different WiFi networks
2. Backend not running
3. Firewall blocking connections

**Solutions:**

**1. Check Same WiFi:**
- iPhone: Settings → Wi-Fi (check network name)
- Computer: Network settings (check network name)
- Must be identical!

**2. Check Services Running:**
```bash
docker-compose ps
```
All 3 containers should show "Up"

**3. Test from Computer First:**
- Visit `http://localhost:5173` on computer
- Should work perfectly
- If not, start services: `docker-compose up -d`

**4. Allow Through Firewall (Windows):**

**Method 1 - GUI:**
1. Windows Security → Firewall
2. Allow an app through firewall
3. Find Docker Desktop → Allow

**Method 2 - Command:**
```bash
netsh advfirewall firewall add rule name="Stock Planner Web" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="Stock Planner API" dir=in action=allow protocol=TCP localport=8000
```

**Method 3 - Quick Test:**
- Temporarily disable firewall
- If it works, add firewall rules
- Re-enable firewall

### **❌ Can't Find IP Address**

**Windows - Multiple Ways:**

```bash
# Method 1
ipconfig

# Method 2
ipconfig | findstr IPv4

# Method 3 (PowerShell)
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias Wi-Fi).IPAddress
```

Look for `192.168.x.x` or `10.0.x.x` under your WiFi adapter

### **❌ Page Loads But No Data**

**Check API Connection:**

On iPhone Safari, visit: `http://YOUR_IP:8000/health`

**Should show:**
```json
{"status":"ok","timezone":"Asia/Kolkata"}
```

**If not:**
- Backend not running → Run `docker-compose up -d`
- Firewall blocking port 8000 → Add firewall rule
- Wrong IP address → Double-check with `ipconfig`

---

## 💡 Pro Tips

### **1. Save IP in iPhone Notes**

Create a note:
```
NiveshDesk
http://192.168.1.214:5173

Updated: Aug 26, 2026
```

Update whenever IP changes!

### **2. Use QR Code**

1. Visit: https://qr-code-generator.com
2. Enter your URL: `http://YOUR_IP:5173`
3. Save QR code image
4. Print or save to iPhone Photos
5. **Scan to access instantly!**

### **3. Set Static IP (Recommended!)**

**Router Settings:**
1. Login to your router (usually `192.168.1.1`)
2. Find DHCP settings
3. Reserve IP for your computer's MAC address
4. Choose a permanent IP like `192.168.1.100`
5. **Never changes again!**

### **4. Use hostname (Advanced)**

**Windows:**
1. Set computer name: Settings → System → About
2. On iPhone: `http://YOUR-COMPUTER-NAME:5173`
3. Example: `http://DESKTOP-ABC123:5173`

**Note:** May not work on all routers

---

## 🌐 Access from Other Devices

Works the same way on:

| Device | Browser | Steps |
|--------|---------|-------|
| **Android Phone** | Chrome/Firefox | Same as iPhone |
| **iPad** | Safari | Same as iPhone |
| **Android Tablet** | Chrome/Firefox | Same as iPhone |
| **Another Laptop** | Any browser | Use same IP:5173 |
| **Smart TV Browser** | Built-in | Use same IP:5173 |

**All devices must be on the same WiFi network!**

---

## 📊 What Works on Mobile

All features are fully functional:

✅ **Dashboard** - See server status  
✅ **Monthly Expenses** - Full functionality  
✅ **Add expenses** - Tap orange + button  
✅ **Edit expenses** - Tap pencil icon  
✅ **Delete expenses** - Tap trash icon  
✅ **Mark as paid** - Large, easy-to-tap checkboxes  
✅ **Filter** - All/Paid/Unpaid buttons  
✅ **Month navigation** - Left/right arrows  
✅ **Smooth scrolling** - Native mobile feel  
✅ **Touch optimized** - 44px+ touch targets  
✅ **iPhone notch support** - Content doesn't hide  
✅ **Landscape mode** - Works both ways  

---

## 🔐 Security

### **Safe Because:**

✅ Only accessible on your **home WiFi network**  
✅ **Not exposed** to the internet  
✅ **Individual password-protected accounts**
✅ **Auto-logout** after 15 minutes of inactivity  

### **Cannot Access From:**

❌ Mobile data (4G/5G)  
❌ Different WiFi network  
❌ Internet / outside your home  
❌ Public WiFi  

**This is intentional for security!**

### **To Access from Anywhere:**

Would require:
- VPN setup
- Or port forwarding on router
- Or cloud deployment

*Not covered in this guide (security risk)*

---

## 📖 Related Guides

- **Mobile Optimization Details:** `MOBILE_GUIDE.md`
- **Email Notifications Setup:** `EXPENSE_NOTIFICATIONS.md`
- **Telegram Bot Setup:** `TELEGRAM_SETUP.md`
- **Full Documentation:** `README.md`

---

## 🎯 Quick Reference Card

**Print this and keep it handy:**

```
┌─────────────────────────────────────────────┐
│     MY EXPENSE TRACKER - MOBILE ACCESS      │
├─────────────────────────────────────────────┤
│                                             │
│  1. Find IP:                                │
│     > ipconfig | findstr IPv4               │
│                                             │
│  2. iPhone Safari:                          │
│     http://YOUR_IP:5173                     │
│                                             │
│  3. Sign in to your private account         │
│                                             │
│  4. Add to Home Screen!                     │
│     Share → Add to Home Screen              │
│                                             │
│  ✓ Works with any IP!                       │
│  ✓ No code changes needed!                  │
│                                             │
└─────────────────────────────────────────────┘
```

---

**Your app now works seamlessly on any device, with any IP! 🎉**
