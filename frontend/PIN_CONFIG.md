# PIN Configuration

## Current PIN
The application PIN is stored in the `.env` file in the frontend directory.

**Current PIN: 1290**

## How to Change the PIN

1. Open the file: `frontend/.env`
2. Change the value of `VITE_PIN_CODE` to your desired 4-digit PIN
3. Rebuild the frontend container:
   ```bash
   docker compose up web --build -d
   ```

## Security Notes

- The `.env` file is already in `.gitignore` and will not be committed to version control
- Keep your PIN confidential
- The PIN is required to access the dashboard and automatically logs out after 15 minutes of inactivity

## File Location
```
stock-planner/
└── frontend/
    └── .env  (PIN stored here)
```
