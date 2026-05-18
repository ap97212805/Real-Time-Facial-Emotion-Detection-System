
const video = document.getElementById("video");
const statusEl = document.getElementById("status");
const emotionBox = document.getElementById("emotionBox");
const confidenceEl = document.getElementById("confidence");

const EMOTIONS = ["angry","disgust","fear","happy","sad","surprise","neutral"];
const EMOJIS = {
  angry:"😠", disgust:"🤢", fear:"😨",
  happy:"😊", sad:"😢", surprise:"😮", neutral:"😐"
};

let stream = null;
let detecting = false;
let intervalId = null;
let buffer = [];
const BUFFER_SIZE = 2;







let customQuestions = [];
let currentQuestionIndex = 0;
let questionTimer = null;
let questionTimeLeft = 0;
let questionIntervals = [];
let lastShownQuestionIndex = -1;









function createPills(){
  emotionBox.innerHTML = "";
  EMOTIONS.forEach(e=>{
    const div = document.createElement("div");
    div.className = "pill " + e;
    div.id = "pill-" + e;
    div.innerHTML = `<span class="emoji">${EMOJIS[e]}</span> ${e}`;
    emotionBox.appendChild(div);
  });
}
createPills();







const EMOTION_COLORS = {
  angry: "#d32f2f",
  disgust: "#7cb342", 
  fear: "#512da8",
  happy: "#fbc02d",
  sad: "#0288d1",
  surprise: "#f57c00",
  neutral: "#757575"
};

async function startCamera(){
  stream = await navigator.mediaDevices.getUserMedia({ video: true });
  video.srcObject = stream;
  statusEl.innerText = "Camera ready";
  // Detection starts when user clicks start button
}
startCamera();





document.getElementById('toggleBtn').innerHTML = '▶ Start';








function toggleDetection(){
  const btn = document.getElementById('toggleBtn');
  if (detecting) {
    stopDetection();
    btn.innerHTML = '▶ Start';
  } else {
    startDetection();
    btn.innerHTML = '⏸ Stop';
  }
}

function startDetection(){
  if (detecting) return;
  detecting = true;
  statusEl.innerText = "Detecting...";
  intervalId = setInterval(captureAndSend, 1500);
}

function stopDetection(){
  detecting = false;
  clearInterval(intervalId);
  highlight(null, 0);
  statusEl.innerText = "Stopped";
}

function captureFrame(){
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video,0,0);
  return canvas.toDataURL("image/jpeg",0.8);
}

async function captureAndSend(){
  const res = await fetch("/predict", {
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({ image: captureFrame() })
  });

  const data = await res.json();
  if (data.emotion === "no_face"){
    highlight(null, 0);
    statusEl.innerText = "No face";
    buffer = [];
    return;
  }

  const face = data.faces[0];
  buffer.push(face.emotion);
  if (buffer.length > BUFFER_SIZE) buffer.shift();

  if (buffer.length === BUFFER_SIZE && buffer.every(e=>e===buffer[0])){
    highlight(face.emotion, face.score);
    statusEl.innerText = `${face.emotion} (${Math.round(face.score*100)}%)`;
  }
}







function highlight(emotion, score){
  EMOTIONS.forEach(e=>{
    const p = document.getElementById("pill-"+e);
    p.classList.remove("active");
    p.style.opacity = "0.5";







    document.getElementById("emotionBar").style.width =
  Math.round(score * 100) + "%";







  });

  if (!emotion){
    confidenceEl.innerText = "Confidence: -";
    return;
  }

  const pill = document.getElementById("pill-"+emotion);
  pill.classList.add("active");
  pill.style.opacity = "1";
  confidenceEl.innerText = `Confidence: ${Math.round(score*100)}%`;

  
  const emotionBar = document.getElementById("emotionBar");
  emotionBar.style.background = EMOTION_COLORS[emotion] || "#067fe9";

  
  checkEmotionAlert(emotion, score);

  updateDisease();



}







function loadSettings(){
  const settings = JSON.parse(localStorage.getItem('emotionSettings') || '{}');
  
  
  if (settings.colors){
    EMOTIONS.forEach(e => {
      const color = settings.colors[e];
      if (color){
        const pill = document.getElementById("pill-"+e);
        if (pill){
          pill.style.color = color;
          pill.style.borderColor = color;
          
          const activeStyle = document.createElement('style');
          activeStyle.innerHTML = `#pill-${e}.active { background: ${color} !important; color: white !important; border-color: ${color} !important; }`;
          document.head.appendChild(activeStyle);
        }
      }
    });
  }
  
  
  if (settings.darkMode){
    document.body.classList.add('dark');
  }
  
  
}


document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  updateDisease(); 
  updateAssessment(); 
});


setInterval(updateDisease, 2000);
setInterval(updateAssessment, 3000); 


updateAssessment();






function getSelectedSessionDurationSeconds() {
  const el = document.getElementById('sessionDurationSelect');
  const seconds = parseInt(el?.value || '60', 10);
  return Math.max(30, seconds);
}

async function startSession(){
  const seconds = getSelectedSessionDurationSeconds();
  sessionEndedAlerted = false; 
  
  
  if (customQuestions.length > 0) {
    console.log("Questions exist, setting up auto-popup:", customQuestions.length);
    const totalSeconds = seconds;
    const interval = totalSeconds / customQuestions.length;
    questionIntervals = [];
    for (let i = 0; i < customQuestions.length; i++) {
      questionIntervals.push(Math.floor(interval * (i + 1)));
    }
    lastShownQuestionIndex = -1;
    
    





    setTimeout(() => {
      console.log("Checking for auto-popup, questions:", customQuestions.length);
      if (customQuestions.length > 0) {
        console.log("Auto-starting question");
        showQuestionModal(0);
        lastShownQuestionIndex = 0;
      } else {
        console.log("No questions, skipping auto-popup");
      }
    }, 5000);
  } else {
    console.log("No questions uploaded, skipping auto-popup setup");
  }
  
  try{
    await fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action: 'start', duration_seconds: seconds })
    });
    updateSessionStatus();
  }catch(e){ console.error('startSession error', e); }
}

async function togglePauseResume(){
  const btn = document.getElementById('pauseSessionBtn');
  const paused = btn.dataset.paused === '1';
  const action = paused ? 'resume' : 'pause';
  try{
    await fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action })
    });
    updateSessionStatus();
  }catch(e){ console.error('togglePauseResume error', e); }
}

async function extendSession(minutes){
  try{
    await fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action: 'extend', minutes })
    });
    updateSessionStatus();
  }catch(e){ console.error('extendSession error', e); }
}

async function updateSessionStatus(){
  try{
    const res = await fetch('/api/session_status');
    const data = await res.json();
    const sessionTimerEl = document.getElementById('sessionTimerDisplay');

    



    if (sessionTimerEl) {
      if (data.remaining_seconds === null) {
        sessionTimerEl.innerText = `Session: Elapsed ${formatTime(data.elapsed_seconds)}`;
        updateProgressBar(0); 
      } else {
        sessionTimerEl.innerText = `Session: Remaining ${formatTime(data.remaining_seconds)}${data.paused ? ' (paused)' : ''}`;

        
        const total = data.elapsed_seconds + data.remaining_seconds;
        const progress = total > 0 ? (data.elapsed_seconds / total) * 100 : 0;
        updateProgressBar(progress);

        
        if (!data.paused && customQuestions.length > 0) {
          const nextQuestionIndex = lastShownQuestionIndex + 1;
          if (nextQuestionIndex < questionIntervals.length && data.elapsed_seconds >= questionIntervals[nextQuestionIndex]) {
            showQuestionModal(nextQuestionIndex);
            lastShownQuestionIndex = nextQuestionIndex;
          }
        }

        


        if (data.remaining_seconds === 0 && !data.paused && !sessionEndedAlerted) {
          sessionEndedAlerted = true;
          triggerSessionEndAlerts();
        }
      }
    }

    const pauseBtn = document.getElementById('pauseSessionBtn');
    if (pauseBtn){
      pauseBtn.dataset.paused = data.paused ? '1' : '0';
      pauseBtn.innerText = data.paused ? '▶ Resume' : '⏸ Pause';
    }
    const modalPauseBtn = document.getElementById('modal-pauseSessionBtn');
    if (modalPauseBtn){
      modalPauseBtn.dataset.paused = data.paused ? '1' : '0';
      modalPauseBtn.innerText = data.paused ? '▶ Resume' : '⏸ Pause';
    }
  }catch(e){ console.error('updateSessionStatus error', e); }
}

function updateProgressBar(progress) {
  const bar = document.getElementById('progressBar');
  const text = document.getElementById('progressText');
  if (bar) bar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
  if (text) text.innerText = `${Math.round(progress)}%`;
}

function formatTime(seconds){
  const s = Math.max(0, parseInt(seconds || 0, 10));
  const m = Math.floor(s/60);
  const sec = s%60;
  return `${m}m ${sec}s`;
}

function startSessionFromModal(){
  const seconds = getSelectedSessionDurationSeconds();
  sessionEndedAlerted = false; 
  
  

  if (customQuestions.length > 0) {
    console.log("Questions exist, setting up auto-popup:", customQuestions.length);
    const totalSeconds = seconds;
    const interval = totalSeconds / customQuestions.length;
    questionIntervals = [];
    for (let i = 0; i < customQuestions.length; i++) {
      questionIntervals.push(Math.floor(interval * (i + 1)));
    }
    lastShownQuestionIndex = -1;
  } else {
    console.log("No questions uploaded, skipping auto-popup setup");
  }
  
  try{
    fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action: 'start', duration_seconds: seconds })
    });
    updateSessionStatus();
  }catch(e){ console.error('startSessionFromModal error', e); }
}


const mainDurationSelect = document.getElementById('sessionDurationSelect');
const modalDurationSelect = document.getElementById('modal-session-duration');
if (mainDurationSelect && modalDurationSelect) {
  mainDurationSelect.addEventListener('change', () => {
    modalDurationSelect.value = mainDurationSelect.value;
  });
  modalDurationSelect.addEventListener('change', () => {
    mainDurationSelect.value = modalDurationSelect.value;
  });
}

function togglePauseResumeFromModal(){
  const btn = document.getElementById('modal-pauseSessionBtn');
  const paused = btn.dataset.paused === '1';
  const action = paused ? 'resume' : 'pause';
  try{
    fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action })
    });
    updateSessionStatus();
  }catch(e){ console.error('togglePauseResumeFromModal error', e); }
}

function extendSessionFromModal(minutes){
  try{
    fetch('/api/session_control', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ action: 'extend', minutes })
    });
    updateSessionStatus();
  }catch(e){ console.error('extendSessionFromModal error', e); }
}
function triggerSessionEndAlerts(){
  
  const modal = document.getElementById("questionModal");
  if (modal && modal.style.display !== "none") {
    closeQuestionModal();
  }
  
  
  const container = document.querySelector('.main') || document.body;
  container.style.backgroundColor = '#ff6b6b';
  setTimeout(() => { container.style.backgroundColor = ''; }, 2000);
  
  
  showSessionEndModal();
  
  
  playSessionEndSound();
  
  
  if (Notification.permission === 'granted') {
    new Notification('Session Completed!', {
      body: 'Interview session has ended. Click to download report.',
      icon: '🎯'
    });
  }
}

function playSessionEndSound(){
  
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const playBeep = (freq, delay) => {
    setTimeout(() => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = freq;
      oscillator.type = 'sine';
      gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    }, delay);
  };
  
  
  playBeep(600, 0);
  playBeep(800, 400);
  playBeep(1000, 800);
}

function showSessionEndModal(){
  
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.8); display: flex; align-items: center;
    justify-content: center; z-index: 10000; font-family: Arial, sans-serif;
  `;
  
  modal.innerHTML = `
    <div style="background: white; padding: 30px; border-radius: 10px; text-align: center; max-width: 400px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
      <h2 style="color: #e74c3c; margin: 0 0 20px 0;">⏰ Session Completed!</h2>
      <p style="margin: 0 0 25px 0; color: #555;">Your interview session has ended. Download your evaluation report below.</p>
      <div style="display: flex; gap: 10px; justify-content: center;">
        <button id="downloadReportBtn" style="background: #27ae60; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold;">📄 Download PDF Report</button>
        <button id="cancelBtn" style="background: #95a5a6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer;">Cancel</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  
  document.getElementById('downloadReportBtn').onclick = () => {
    window.open('/api/generate_report', '_blank');
    modal.remove();
  };
  
  
  document.getElementById('cancelBtn').onclick = () => {
    modal.remove();
    
    const questionModal = document.getElementById('questionModal');
    if (questionModal) {
      questionModal.style.display = 'none';
    }
  };
  
  
  setTimeout(() => {
    if (modal.parentNode) {
      modal.remove();
    }
  }, 30000);
}


setInterval(updateSessionStatus, 1000);
updateSessionStatus();




function checkEmotionAlert(emotion, score) {
  const settings = JSON.parse(localStorage.getItem('emotionSettings') || '{}');
  if (!settings.alerts || !settings.alerts.enabled) return;
  
  if (emotion === settings.alerts.emotion && score >= settings.alerts.threshold / 100) {
    triggerAlert(emotion, score);
  }
}

function triggerAlert(emotion, score) {
  const settings = JSON.parse(localStorage.getItem('emotionSettings') || '{}');
  
  


  if (settings.alerts.sound) {
    playAlertSound();
  }
  
  



  if (settings.alerts.browser && Notification.permission === 'granted') {
    new Notification(`Emotion Alert: ${emotion}`, {
      body: `Confidence: ${Math.round(score * 100)}%`,
      icon: '🔔'
    });
  }
  
  




  if (settings.alerts.visual) {
    const container = document.querySelector('.main') || document.body;
    container.style.backgroundColor = '#fff3cd';
    setTimeout(() => { container.style.backgroundColor = ''; }, 1000);
  }
}

function playAlertSound() {
  
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  
  oscillator.frequency.value = 800;
  oscillator.type = 'sine';
  gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
  
  oscillator.start(audioContext.currentTime);
  oscillator.stop(audioContext.currentTime + 0.5);
}

async function resetSession(){
  await fetch("/api/reset",{method:"POST"});
  buffer = [];
  highlight(null,0);
  statusEl.innerText = "Session reset";
}








async function updateDisease(){
  const res = await fetch("/api/predict_disease");
  const data = await res.json();
  const box = document.getElementById("diseaseList");

  if (!data.emotion || data.emotion === "No data") {
    box.innerHTML = '<div style="color:#666;font-size:0.9rem;">Analyzing emotions...</div>';
    return;
  }

  let html = `<div style="margin-bottom:8px;font-weight:900;color:#000;"><strong>Current Emotion:</strong> ${data.emotion.charAt(0).toUpperCase() + data.emotion.slice(1)} (${Math.round(data.confidence * 100)}%)</div>`;

  if (Object.keys(data.diseases).length === 0) {
    html += '<div style="color:#28a745;font-size:0.9rem;font-weight:900;">✅ No significant health risks detected</div>';
  } else {
    html += '<div style="margin-top:8px;font-weight:900;color:#000;"><strong>Potential Health Risks:</strong></div>';
    for (const [disease, percentage] of Object.entries(data.diseases)) {
      const riskLevel = percentage >= 70 ? 'high' : percentage >= 40 ? 'medium' : 'low';
      const color = riskLevel === 'high' ? '#a32431ff' : riskLevel === 'medium' ? '#d2a213ff' : '#37a951ff';
      html += `<div style="margin:4px 0;padding:4px 8px;border-radius:4px;background:${color}20;border-left:3px solid ${color};">
        <span style="font-weight:900;color:#000;">${disease}:</span> <span style="color:${color};font-weight:700;">${percentage}%</span>
      </div>`;
    }
  }

  box.innerHTML = html;
}

async function updateAssessment(){
  try {
    const res = await fetch("/api/assessment");
    const data = await res.json();

    console.log("Assessment data:", data); 

    document.getElementById("nervousness-level").innerText = `Nervousness: ${data.nervousness || 0}%`;
    document.getElementById("hr-assessment").innerText = `HR Score: ${data.hr_assessment || 0}/100`;

    
    updateFeedbackMessage(data);
  } catch (error) {
    console.error("Error updating assessment: ⚠️", error);
  }
}

function updateFeedbackMessage(data) {
  const feedbackEl = document.getElementById("feedbackMessage");
  if (!feedbackEl) {
    console.error("Feedback element not found");
    return;
  }

  let message = "Keep going! You're doing well. 👍 🌟 💪";
  const nervousness = data.nervousness || 0;
  const hrScore = data.hr_assessment || 0;
  const frequency = data.frequency_count || 0;

  console.log("Feedback data:", { nervousness, hrScore, frequency });

  if (nervousness > 70) {
    message = "Try to relax and take deep breaths. You're showing signs of high nervousness. 😌 🧘‍♂️ 🌬️";
  } else if (nervousness > 50) {
    message = "You're a bit nervous. Focus on your breathing to stay calm. 🙂 🌿 😮‍💨";
  } else if (hrScore > 80) {
    message = "Excellent performance! Your HR score is very high. 🚀 🏆 📈";
  } else if (hrScore > 60) {
    message = "Good job! You're performing well in this interview. 👏 😊 ✅";
  } else if (frequency > 150) {
    message = "You're speaking quite fast. Try to slow down a bit for clarity. 🐢 ⏸️ 🎤";
  } else if (frequency < 100 && frequency > 0) {
    message = "Consider speaking a bit faster to show enthusiasm. ⚡ 🎤 😃";
  }

  feedbackEl.innerText = message;
  console.log("Feedback updated:", message);
}




function addQuestion() {
  if (customQuestions.length >= 5) {
    alert("Maximum 5 questions allowed");
    return;
  }
  
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = `Question ${customQuestions.length + 1}`;
  input.style.cssText = "flex:1;padding:6px;margin:4px 0;border:1px solid #ddd;border-radius:4px;";
  
  const timerSelect = document.createElement("select");
  timerSelect.style.cssText = "padding:4px;margin:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:0.8rem;width:120px;";
  const timerOptions = [15,25,35,45,55,65,75,85,95,105,115,120];
  timerOptions.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.text = `${t}s`;
    timerSelect.appendChild(opt);
  });
  timerSelect.value = 30; 
  
  const removeBtn = document.createElement("button");
  removeBtn.innerText = "❌";
  removeBtn.style.cssText = "margin-left:8px;padding:4px 8px;border:none;background:#ff6b6b;color:white;border-radius:4px;cursor:pointer;";
  removeBtn.onclick = () => {
    const index = customQuestions.findIndex(q => q.input === input);
    if (index > -1) {
      customQuestions.splice(index, 1);
      updateQuestionInputs();
    }
  };
  
  const container = document.createElement("div");
  container.style.cssText = "display:flex;align-items:center;margin:4px 0;";
  container.appendChild(input);
  container.appendChild(timerSelect);
  container.appendChild(removeBtn);
  
  const statusIcon = document.createElement("span");
  statusIcon.innerText = "⏳";
  statusIcon.style.cssText = "margin-left:8px;font-size:1.2rem;";
  container.appendChild(statusIcon);
  
  const questionObj = { text: "", input: input, timerSelect: timerSelect, container: container, completed: false, statusIcon: statusIcon };
  customQuestions.push(questionObj);
  
  input.oninput = () => {
    questionObj.text = input.value;
  };
  
  timerSelect.onchange = () => {
    questionObj.timer = parseInt(timerSelect.value);
  };
  questionObj.timer = 30; 
  
  document.getElementById("questionInputs").appendChild(container);
  
  
  updateTimerModeVisibility();
}

function updateQuestionInputs() {
  const container = document.getElementById("questionInputs");
  container.innerHTML = "";
  customQuestions.forEach(q => {
    container.appendChild(q.container);
    
    if (q.timerSelect) {
      q.timerSelect.style.display = document.querySelector('input[name="timerMode"]:checked').value === 'individual' ? 'block' : 'none';
    }
  });
}

function updateTimerModeVisibility() {
  const mode = document.querySelector('input[name="timerMode"]:checked').value;
  document.getElementById("commonTimerDiv").style.display = mode === 'common' ? 'block' : 'none';
  updateQuestionInputs();
}


document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[name="timerMode"]').forEach(radio => {
    radio.addEventListener('change', updateTimerModeVisibility);
  });
  updateTimerModeVisibility(); 
});

function startQuestions() {
  startSessionFromModal();
  showQuestionModal(0);
}

function showQuestionModal(index = 0) {
  if (customQuestions.length === 0) return;
  
  currentQuestionIndex = Math.max(0, Math.min(index, customQuestions.length - 1));
  const question = customQuestions[currentQuestionIndex];
  
  
  question.completed = true;
  question.statusIcon.innerText = "✅";
  question.statusIcon.style.color = "#28a745";
  
  document.getElementById("questionTitle").innerText = `Question ${currentQuestionIndex + 1}/${customQuestions.length}`;
  document.getElementById("questionText").innerText = question.text || "No question text";
  
  document.getElementById("prevBtn").disabled = currentQuestionIndex === 0;
  document.getElementById("nextBtn").disabled = currentQuestionIndex === customQuestions.length - 1;
  
  const modal = document.getElementById("questionModal");
  const wasModalOpen = modal.style.display === "flex";
  modal.style.display = "flex";
  
  


  const mainDuration = getSelectedSessionDurationSeconds();
  const modalDurationSelect = document.getElementById('modal-session-duration');
  if (modalDurationSelect) {
    modalDurationSelect.value = mainDuration;
  }
  
  
  const modalDiv = modal.querySelector('div');
  modalDiv.style.left = '50%';
  modalDiv.style.top = '50%';
  modalDiv.style.transform = 'translate(-50%, -50%)';
  
  
  





  
  startQuestionTimer();
}

function closeQuestionModal() {
  document.getElementById("questionModal").style.display = "none";
  if (questionTimer) {
    clearInterval(questionTimer);
    questionTimer = null;
  }
  
  fetch('/api/session_control', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ action: 'end' })
  }).then(() => {
    updateSessionStatus();
  }).catch(e => console.error('Error ending session:', e));
}

function navigateQuestion(direction) {
  const newIndex = currentQuestionIndex + direction;
  if (newIndex >= 0 && newIndex < customQuestions.length) {
    showQuestionModal(newIndex);
  }
}

function startQuestionTimer() {
  if (questionTimer) clearInterval(questionTimer);
  
  const mode = document.querySelector('input[name="timerMode"]:checked').value;
  let totalTime;
  if (mode === 'common') {
    totalTime = parseInt(document.getElementById("commonQuestionTimer").value) || 30;
  } else {
    const question = customQuestions[currentQuestionIndex];
    totalTime = question.timer || 30;
  }
  questionTimeLeft = totalTime;
  
  updateQuestionTimerDisplay();
  
  questionTimer = setInterval(() => {
    
    const pauseBtn = document.getElementById('modal-pauseSessionBtn');
    const isPaused = pauseBtn && pauseBtn.dataset.paused === '1';
    
    if (!isPaused) {
      questionTimeLeft--;
      updateQuestionTimerDisplay();
      
      if (questionTimeLeft <= 0) {
        clearInterval(questionTimer);
        questionTimer = null;
        
        fetch('/api/session_status').then(res => res.json()).then(data => {
          if (data.remaining_seconds !== null && data.remaining_seconds > 0 && !data.paused) {
            
            const nextIndex = (currentQuestionIndex + 1) % customQuestions.length;
            showQuestionModal(nextIndex);
          } else {
            
            closeQuestionModal();
          }
        }).catch(e => {
          console.error('Error checking session status:', e);
          closeQuestionModal();
        });
      }
    } else {
      
      updateQuestionTimerDisplay();
    }
  }, 1000);
}

function updateQuestionTimerDisplay() {
  const display = document.getElementById("questionTimerDisplay");
  const progressBar = document.getElementById("questionProgressBar");
  
  display.innerText = `Time: ${questionTimeLeft}s`;
  
  const mode = document.querySelector('input[name="timerMode"]:checked').value;
  let totalTime;
  if (mode === 'common') {
    totalTime = parseInt(document.getElementById("commonQuestionTimer").value) || 30;
  } else {
    const question = customQuestions[currentQuestionIndex];
    totalTime = question.timer || 30;
  }
  const progress = ((totalTime - questionTimeLeft) / totalTime) * 100;
  progressBar.style.width = `${Math.max(0, progress)}%`;
  
  if (questionTimeLeft <= 10) {
    display.style.color = "#e74c3c";
  } else {
    display.style.color = "#0488fb";
  }
}


document.addEventListener("DOMContentLoaded", () => {
  
  if (customQuestions.length === 0) {
    addQuestion();
  }
});


let isDragging = false;
let dragOffsetX = 0;
let dragOffsetY = 0;

document.addEventListener('mousedown', (e) => {
  if (e.target.closest('#questionModal > div')) {
    const modal = e.target.closest('#questionModal > div');
    isDragging = true;
    dragOffsetX = e.clientX - modal.offsetLeft;
    dragOffsetY = e.clientY - modal.offsetTop;
    modal.style.position = 'absolute';
  }
});

document.addEventListener('mousemove', (e) => {
  if (isDragging) {
    const modal = document.querySelector('#questionModal > div');
    if (modal) {
      modal.style.left = (e.clientX - dragOffsetX) + 'px';
      modal.style.top = (e.clientY - dragOffsetY) + 'px';
    }
  }
});

document.addEventListener('mouseup', () => {
  isDragging = false;
});
