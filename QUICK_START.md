# 🚀 Arun's Stock Planner - Quick Start Guide

## ✅ Your App is Running!

**Access your Stock Planner:**
- 🌐 **Website**: http://localhost:5173
- 📚 **API Docs**: http://localhost:8000/docs
- 🖥️ **Desktop Shortcut**: "Arun's Stock Planner" on your desktop

---

## 🎯 Easy Commands

Located in: `c:\Users\arunkumar\Arun\Personal\AI-Project\my-stock-planner\stock-planner\`

### **START.bat**
- Starts all containers
- Opens app in browser automatically
- **Double-click to launch!**

### **STOP.bat**
- Stops all containers gracefully
- Use when done for the day

### **STATUS.bat**
- Check if app is running
- See container status

---

## 🎨 Features

✅ **Real-time Stock Prices** - Live NSE data via yfinance  
✅ **Market Status Indicator** - See if market is open/closed  
✅ **Live Market Indices** - SENSEX, NIFTY 50, NIFTY BANK  
✅ **Day Change Indicators** - Green ↑ / Red ↓ with percentages  
✅ **Configurable Budget** - Click to edit monthly investment  
✅ **Smart Filters** - Search, status, market cap filters  
✅ **Company Logos** - Visual stock identification  
✅ **Font Awesome Icons** - Professional UI throughout  
✅ **Live Price Dots** - Pulsing indicators for real-time data  
✅ **Auto-Redistribution** - Budget changes recalculate all stocks  

---

## 💰 How to Use

### **Change Your Budget:**
1. Click on "₹35,000 / month" heading
2. Enter new amount (e.g., 50000, 25000)
3. Click **✓ Apply**
4. Watch stocks automatically redistribute!

### **Filter Stocks:**
- **Search** by name or symbol
- **Status**: Show only BUY or WAIT
- **Cap**: Filter by Large/Mid/Small cap

### **Refresh Prices:**
- Click "Refresh prices" button
- Updates all stock data from market

---

## 📊 Understanding the Dashboard

### **Market Banner** (Top)
- 🟢 Green = Market Open (Mon-Fri, 9:15 AM - 3:30 PM)
- 🔴 Red = Market Closed
- Live indices with day changes

### **Stats Cards**
- **Budget**: Your monthly investment limit
- **Suggested Deployment**: Total recommended this month
- **Reserve**: Money left over
- **Holdings**: Number of stocks tracked

### **Stock Table**
- **Price Column**: 
  - Line 1: Current price with live dot (🟢)
  - Line 2: Day change with ↑/↓ arrow
- **Status**:
  - 🛒 **BUY**: Price in target range
  - ⏳ **WAIT**: Price too high

---

## 🔧 Technical Details

**Stack:**
- **Frontend**: React + Vite + TypeScript
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL 16
- **Market Data**: yfinance (Yahoo Finance)
- **Icons**: Font Awesome 6.5.1
- **Container**: Docker + Docker Compose

**Ports:**
- Frontend: 5173
- Backend API: 8000
- PostgreSQL: 5432

---

## 🆘 Troubleshooting

### **App won't start?**
1. Check Docker Desktop is running (whale icon in tray)
2. Run `START.bat`
3. Wait 10 seconds for containers to start

### **Can't access http://localhost:5173?**
1. Run `STATUS.bat` to check containers
2. Make sure all 3 containers show "Up"
3. Try refreshing browser (Ctrl + F5)

### **Price data not loading?**
- Internet connection required
- yfinance API might be rate-limited
- Try clicking "Refresh prices" after a few seconds

### **Desktop shortcut not working?**
- Make sure Docker is running first
- Run `START.bat` to start containers
- Then use desktop shortcut

---

## 📝 Daily Workflow

**Morning:**
1. Start Docker Desktop
2. Double-click `START.bat` OR desktop shortcut
3. App opens automatically in browser

**During Day:**
- Check market status (green = open)
- Review BUY recommendations
- Adjust budget if needed
- Refresh prices periodically

**Evening:**
- Review your portfolio
- Note down BUY recommendations
- Double-click `STOP.bat` to stop containers

---

## 🎉 Enjoy Your Stock Planner!

Made with ❤️ by Arun Kumar  
© 2026 All Rights Reserved

**Questions or Issues?**  
Check the README.md for detailed documentation.
