# PharmaVerify Demo Guide

## Run
1. Extract the ZIP.
2. Open PowerShell in the folder containing `app.py`.
3. Run `python -m pip install -r requirements.txt` then `python app.py`.
4. Open `http://127.0.0.1:5000`.

## Admin demo login
- Username: `admin`
- Password: `admin123`

## Demo records
The app seeds 100 additional fictional sample batch records across 10 medicine categories (106+ total including the original records). Manufacturers, batches, prices, and record expiries are fictional academic-demo data and must not be treated as commercial information. Sample price values are not live market prices.

## Photo demo
Open Scan Barcode, upload a clear photo of a medicine strip/box, and click Identify from Photo & Show Details. OCR reads visible text in the browser and tries to match a known medicine name. The app then shows the matched demo record, sample manufacturer, batch, manufacturing date, expiry status, sample price, general uses, and safety notes. The expiry shown is from the demo database, not necessarily the uploaded package. Always compare the real package.

## Important limitations
- Loose tablet appearance alone cannot reliably identify a medicine.
- OCR can misread text; photo matching does not verify authenticity, batch, manufacturer, price, or actual expiry.
- Medicine uses and precautions are general educational notes, not individual treatment instructions. Never use fictional demo data to decide whether to take a medicine.
- This project uses a local hash-linked audit log; the sample Solidity contract is not deployed or connected to a live blockchain.
