(function () {
  let scanner = null;
  let busy = false;

  function statusBox(readerId) {
    return document.getElementById(readerId + "-status");
  }
  function show(readerId, text, type) {
    const area = statusBox(readerId);
    if (!area) return;
    area.textContent = "";
    const msg = document.createElement("div");
    msg.className = "alert alert-" + (type || "info") + " mt-2";
    msg.textContent = text;
    area.appendChild(msg);
  }
  async function stopScanner() {
    if (scanner) {
      try { if (scanner.isScanning) await scanner.stop(); } catch (e) {}
      try { scanner.clear(); } catch (e) {}
      scanner = null;
    }
    busy = false;
  }
  async function start(readerId, inputId, autoSubmit) {
    const reader = document.getElementById(readerId);
    const input = document.getElementById(inputId);
    if (!reader || !input || busy) return;
    await stopScanner();
    busy = true;
    reader.innerHTML = "";
    show(readerId, "Requesting camera access…", "info");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      show(readerId, "Camera API unavailable. Use Chrome at http://127.0.0.1:5000 and enter barcode manually if needed.", "danger");
      busy = false; return;
    }
    if (!window.Html5Qrcode) {
      show(readerId, "Barcode scanner library did not load. Check internet, then press Ctrl+Shift+R.", "danger");
      busy = false; return;
    }

    try {
      // Let the scanner library acquire the camera itself; don't open/close a temporary stream.
      const cameras = await Html5Qrcode.getCameras();
      if (!cameras || cameras.length === 0) {
        show(readerId, "Chrome reports no camera device. Test Windows Camera and check Device Manager > Cameras.", "danger");
        busy = false; return;
      }
      const chosen = cameras.find(c => /back|rear|environment/i.test(c.label)) || cameras[0];
      scanner = new Html5Qrcode(readerId);
      await scanner.start(
        chosen.id,
        { fps: 10, qrbox: { width: 280, height: 150 }, aspectRatio: 1.777 },
        async function (decodedText) {
          input.value = decodedText;
          show(readerId, "Barcode captured: " + decodedText, "success");
          const current = scanner;
          if (current) {
            try { if (current.isScanning) await current.stop(); } catch (e) {}
            try { current.clear(); } catch (e) {}
            scanner = null;
          }
          busy = false;
          if (autoSubmit && input.closest("form")) input.closest("form").submit();
        },
        function () {}
      );
      // IMPORTANT: status is rendered outside the video reader so we don't remove the camera video.
      show(readerId, "Camera is on. Hold the barcode steady inside the scanning box.", "info");
    } catch (err) {
      await stopScanner();
      let msg = "Scanner could not start. " + (err.message || "Check camera settings.");
      if (err.name === "NotAllowedError" || err.name === "SecurityError")
        msg = "Camera permission denied. Allow camera for 127.0.0.1:5000 in Chrome Site settings.";
      else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError")
        msg = "No camera found. Connect/enable a webcam or enter the barcode manually.";
      else if (err.name === "NotReadableError" || err.name === "TrackStartError")
        msg = "Camera is busy. Close Windows Camera, Teams, Zoom, or other apps using it, then retry.";
      show(readerId, msg, "danger");
      busy = false;
    }
  }
  window.startAdminScanner = function () { start("admin-reader", "barcode", false); };
  window.startLookupScanner = function () { start("lookup-reader", "lookup-code", true); };
  window.addEventListener("beforeunload", function () { stopScanner(); });
})();
// OCR helper: reads printed expiry text from medicine packaging, not from a bare tablet.
let expiryStream = null;
window.startExpiryCamera = async function () {
  const video = document.getElementById('expiry-video');
  const status = document.getElementById('expiry-status');
  try {
    if (expiryStream) window.stopExpiryCamera();
    expiryStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    video.srcObject = expiryStream; video.style.display = 'block';
    await video.play();
    document.getElementById('ocr-capture').disabled = false;
    status.className = 'alert alert-info mt-2';
    status.textContent = 'Camera on. Keep EXP/Expiry and date text on the strip or box clearly visible, then tap Capture & read expiry.';
  } catch (e) {
    status.className = 'alert alert-danger mt-2';
    status.textContent = 'Could not open camera. Allow camera permission and close other camera apps. ' + (e.message || '');
  }
};
window.stopExpiryCamera = function () {
  if (expiryStream) { expiryStream.getTracks().forEach(t => t.stop()); expiryStream = null; }
  const v = document.getElementById('expiry-video'); if (v) { v.pause(); v.srcObject = null; v.style.display = 'none'; }
  const b = document.getElementById('ocr-capture'); if (b) b.disabled = true;
};
window.readExpiryText = async function () {
  const video = document.getElementById('expiry-video'), canvas = document.getElementById('expiry-canvas');
  const status = document.getElementById('expiry-status'), output = document.getElementById('expiry-ocr-text');
  if (!video || !video.videoWidth) { status.className='alert alert-warning'; status.textContent='First open the expiry-text camera.'; return; }
  if (!window.Tesseract) { status.className='alert alert-danger'; status.textContent='Text reader library did not load. Check internet and refresh the page.'; return; }
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  status.className='alert alert-info'; status.textContent='Reading printed text… please wait.';
  try {
    const result = await Tesseract.recognize(canvas, 'eng');
    const text = (result.data.text || '').replace(/\s+/g, ' ').trim(); output.textContent = 'Detected text: ' + (text || '(none)');
    const patterns = [/(?:EXP(?:IRY)?|EXD|USE\s*BY|BEST\s*BEFORE)\s*[:.-]?\s*((?:0?[1-9]|1[0-2])[\/-](?:20)?\d{2}|(?:0?[1-9]|[12]\d|3[01])[\/-](?:0?[1-9]|1[0-2])[\/-](?:20)?\d{2}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[ -]?(?:20)?\d{2})/i,
      /(?:EXP(?:IRY)?|EXD|USE\s*BY|BEST\s*BEFORE)[^0-9A-Z]{0,8}((?:0?[1-9]|1[0-2])[\/-](?:20)?\d{2})/i];
    let match = null; for (const re of patterns) { match = text.match(re); if (match) break; }
    if (match) {
      const raw = match[1];
      status.className='alert alert-warning';
      status.textContent='Possible expiry text detected: ' + raw + '. Please verify it visually on the package; OCR can misread characters. This does not confirm authenticity.';
    } else {
      status.className='alert alert-warning';
      status.textContent='Could not confidently detect an EXP/Expiry date. Move closer, improve lighting, include the EXP label and date, and try again. A bare tablet cannot reveal its expiry date.';
    }
  } catch (e) { status.className='alert alert-danger'; status.textContent='Text reading failed: ' + (e.message || 'try again'); }
};

// Camera label OCR: reads visible printed label text, then matches only known demo records.
let identifyStream = null;
window.startMedicineCamera = async function () {
  const video = document.getElementById('identify-video');
  const status = document.getElementById('identify-status');
  try {
    if (identifyStream) window.stopMedicineCamera();
    identifyStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    video.srcObject = identifyStream; video.style.display = 'block'; await video.play();
    document.getElementById('identify-capture').disabled = false;
    status.className = 'alert alert-info mt-2';
    status.textContent = 'Camera ready. Keep the medicine name and EXP date on the strip/box in focus, then tap Capture & Identify.';
  } catch (e) {
    status.className = 'alert alert-danger mt-2';
    status.textContent = 'Camera could not open. Allow camera access in Chrome and close other camera apps. ' + (e.message || '');
  }
};
window.stopMedicineCamera = function () {
  if (identifyStream) { identifyStream.getTracks().forEach(t => t.stop()); identifyStream = null; }
  const v = document.getElementById('identify-video'); if (v) { v.pause(); v.srcObject = null; v.style.display = 'none'; }
  const b = document.getElementById('identify-capture'); if (b) b.disabled = true;
};
window.identifyMedicineFromLabel = async function () {
  const video = document.getElementById('identify-video');
  const canvas = document.getElementById('identify-canvas');
  const status = document.getElementById('identify-status');
  const resultBox = document.getElementById('identify-result');
  if (!video || !video.videoWidth) { status.className='alert alert-warning'; status.textContent='First tap “Tap to Identify Medicine”.'; return; }
  if (!window.Tesseract) { status.className='alert alert-danger'; status.textContent='OCR library did not load. Check internet and refresh.'; return; }
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  status.className='alert alert-info'; status.textContent='Reading label text… please wait.';
  try {
    const ocr = await Tesseract.recognize(canvas, 'eng');
    const text = (ocr.data.text || '').replace(/\s+/g, ' ').trim();
    const normalized = text.toLowerCase();
    const known = [
      {terms:['paracetamol','acetaminophen'], code:'DEMO-PARA-001'},
      {terms:['cetirizine'], code:'DEMO-CET-002'},
      {terms:['vitamin c','ascorbic acid'], code:'DEMO-VITC-003'},
      {terms:['ors','oral rehydration'], code:'DEMO-ORS-004'},
      {terms:['antacid'], code:'DEMO-ANTI-005'},
      {terms:['cough syrup'], code:'DEMO-COUGH-006'},
      {terms:['ibuprofen'],name:'Ibuprofen',code:'DEMO-EXTRA-007',uses:'Some pain and inflammation relief uses; not suitable for everyone.',when:'Only when the exact product label or a clinician says it is appropriate.',safety:'May not be suitable for people with stomach ulcers, kidney disease, some asthma, pregnancy, or certain other medicines. Ask a pharmacist.'},
      {terms:['amoxicillin'],name:'Amoxicillin',code:'DEMO-EXTRA-008',uses:'Prescription antibiotic for certain bacterial infections.',when:'Only when prescribed by a qualified clinician.',safety:'Do not self-start or share antibiotics. Follow the prescription and ask about penicillin allergy.'},
      {terms:['calcium','vitamin d3'],name:'Calcium + Vitamin D3',code:'DEMO-EXTRA-009',uses:'Supplement to support calcium and vitamin D intake when indicated.',when:'When recommended based on dietary needs or professional advice.',safety:'Follow label directions; check with a clinician if you have kidney problems or take other medicines.'},
      {terms:['pantoprazole'],name:'Pantoprazole',code:'DEMO-EXTRA-010',uses:'Reduces stomach acid for certain conditions.',when:'Use as directed by a clinician or the exact product label.',safety:'Do not use long-term without medical advice; persistent symptoms need assessment.'}
    ];
    const match = known.find(item => item.terms.some(term => normalized.includes(term)));
    resultBox.innerHTML = '';
    const detected = document.createElement('p'); detected.className='small text-secondary'; detected.textContent='Text detected by OCR: ' + (text || '(no readable text)'); resultBox.appendChild(detected);
    if (match) {
      const form = document.createElement('form'); form.method='post'; form.action='/barcode-lookup';
      const input = document.createElement('input'); input.type='hidden'; input.name='barcode'; input.value=match.code; form.appendChild(input);
      resultBox.appendChild(form);
      status.className='alert alert-success'; status.textContent='Possible medicine name recognized: ' + match.terms[0] + '. Checking the registered demo record…';
      form.submit();
    } else {
      status.className='alert alert-warning';
      status.textContent='Could not match the printed text to a known demo medicine. Try clearer focus/lighting or enter the medicine name/batch number manually. A camera cannot reliably identify a loose tablet or prove authenticity.';
    }
  } catch (e) { status.className='alert alert-danger'; status.textContent='OCR failed: ' + (e.message || 'please try again'); }
};


// Upload a medicine-package image and read visible label text with browser OCR.
window.previewMedicinePhoto = function (event) {
  const file = event.target.files && event.target.files[0];
  const preview = document.getElementById('medicine-photo-preview');
  const status = document.getElementById('photo-identify-status');
  const result = document.getElementById('photo-identify-result');
  result.innerHTML = '';
  if (!file) { preview.style.display = 'none'; return; }
  if (!file.type.startsWith('image/')) { status.className='alert alert-warning'; status.textContent='Please select an image file.'; return; }
  preview.src = URL.createObjectURL(file);
  preview.style.display = 'block';
  status.className='alert alert-info';
  status.textContent='Photo selected. Click “Identify from Photo & Show Details”.';
};
window.identifyMedicineFromPhoto = async function () {
  const input = document.getElementById('medicine-photo');
  const status = document.getElementById('photo-identify-status');
  const resultBox = document.getElementById('photo-identify-result');
  const file = input && input.files && input.files[0];
  resultBox.innerHTML = '';
  if (!file) { status.className='alert alert-warning'; status.textContent='First upload a clear medicine strip/box photo.'; return; }
  if (!window.Tesseract) { status.className='alert alert-danger'; status.textContent='OCR library did not load. Check internet and refresh the page.'; return; }
  status.className='alert alert-info'; status.textContent='Reading text from image… first use may take a minute.';
  try {
    const ocr = await Tesseract.recognize(file, 'eng');
    const raw = (ocr.data.text || '').replace(/\s+/g, ' ').trim();
    const norm = raw.toLowerCase();
    const items = [
      {terms:['paracetamol','acetaminophen','dolo 500','dolo'],name:'Paracetamol',code:'DEMO-PARA-001',uses:'Commonly used to relieve mild-to-moderate pain and reduce fever.',when:'For pain or fever only when the label/health professional says it is appropriate.',safety:'Do not combine with other products containing paracetamol. Too much can cause severe liver damage. Follow the pack dose; ask a pharmacist if unsure.'},
      {terms:['cetirizine'],name:'Cetirizine',code:'DEMO-CET-002',uses:'An antihistamine commonly used for allergy symptoms such as sneezing, runny nose and itching.',when:'For allergy symptoms when suitable for the person and as directed on the package or by a clinician.',safety:'May cause sleepiness. Check age directions and ask a pharmacist about other medicines or health conditions.'},
      {terms:['vitamin c','ascorbic acid'],name:'Vitamin C',code:'DEMO-VITC-003',uses:'A vitamin supplement that helps meet vitamin C needs.',when:'As a supplement when needed and according to the product label; it is not a treatment for every illness.',safety:'Follow the label and avoid taking more than directed.'},
      {terms:['ors','oral rehydration salts'],name:'ORS',code:'DEMO-ORS-004',uses:'Oral rehydration salts help replace water and salts lost through diarrhoea or vomiting.',when:'Dissolve the full sachet in exactly the amount of clean water stated on its packet.',safety:'Do not guess the water amount or add extra sugar/salt. Seek medical care for severe dehydration, confusion or inability to drink.'},
      {terms:['antacid'],name:'Antacid',code:'DEMO-ANTI-005',uses:'Some antacids give short-term relief from heartburn or indigestion.',when:'Only for symptoms described on the exact product label; ingredients vary by brand.',safety:'Ask a pharmacist if symptoms persist, you have kidney disease, or you take other medicines.'},
      {terms:['cough syrup'],name:'Cough syrup',code:'DEMO-COUGH-006',uses:'Cough syrups have different ingredients and are intended for different types of cough.',when:'Only after checking the exact ingredients and label instructions.',safety:'Do not use an unidentified syrup or combine cough/cold medicines without pharmacist advice. Age limits matter.'}
    ];
    const match = items.find(x => x.terms.some(term => norm.includes(term)));
    const textEl = document.createElement('div'); textEl.className='alert alert-secondary';
    textEl.innerHTML='<strong>Text read from photo (OCR)</strong><div></div>';
    textEl.lastElementChild.textContent = raw || 'No readable text detected. Try a sharper, brighter photo of the printed label.';
    resultBox.appendChild(textEl);
    if (!match) {
      status.className='alert alert-warning';
      status.textContent='Medicine name was not confidently recognized. Please upload a clearer photo showing the printed name and composition, or type the name to ask a pharmacist. No medicine identity or expiry has been confirmed.';
      return;
    }
    status.className='alert alert-info'; status.textContent='Possible label name found. Loading registered demo details…';
    try {
      const response = await fetch('/api/demo-medicine/' + encodeURIComponent(match.code));
      if (!response.ok) throw new Error('No registered demo record for this match.');
      const data = await response.json();
      const card=document.createElement('div'); card.className='card p-3';
      const heading=document.createElement('h4'); heading.textContent='Possible match: '+data.name; card.appendChild(heading);
      const badge=document.createElement('span'); badge.className='badge text-bg-warning align-self-start'; badge.textContent='DEMO DATABASE RECORD'; card.appendChild(badge);
      const make=(title,body)=>{const h=document.createElement('h6');h.className='mt-3 mb-1';h.textContent=title;card.appendChild(h);const p=document.createElement('p');p.className='mb-1';p.textContent=body || 'Not available in this demo record';card.appendChild(p);};
      make('Manufacturer (fictional demo)', data.manufacturer);
      make('Composition / strength', data.composition);
      make('Batch number', data.batch_no);
      make('Manufacturing date', data.mfg_date);
      make('Expiry date in demo record (not verified from this photo)', data.expiry_date);
      make('Expiry status', data.status);
      make('Sample price (not a live market price)', data.price);
      make('What is it used for?', data.uses);
      make('When is it used?', data.when_used);
      make('Safety / precautions', data.safety);
      const small=document.createElement('p');small.className='small text-danger mt-3 mb-0';small.textContent='Academic demo only: OCR name matching does not verify the actual batch, manufacturer, price, authenticity, or expiry. Compare every field with the physical package and ask a pharmacist. Do not use these demo details for treatment.';card.appendChild(small);
      resultBox.appendChild(card);
      status.className='alert alert-success'; status.textContent='Possible medicine name detected. Full demo details are shown below; verify the physical package.';
    } catch (err) {
      status.className='alert alert-warning'; status.textContent='Name detected but no registered demo record was found for this code. Do not guess the expiry or manufacturer.';
    }
  } catch (e) {
    status.className='alert alert-danger'; status.textContent='Could not read the photo: '+(e.message || 'please try a clearer image.');
  }
};
