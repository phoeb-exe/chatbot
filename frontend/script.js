async function sendMessage() {
  const input = document.getElementById("message").value.trim();
  if (!input) return;

  const log = document.getElementById("chatlog");

  const userBubble = document.createElement("div");
  userBubble.className = "user";
  userBubble.innerText = input;
  log.appendChild(userBubble);

  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: input })
  });

  const data = await response.json();
  const feedbackId = `fb-${Date.now()}`;
  const botReply = data.reply;

  const botBubble = document.createElement("div");
  botBubble.className = "bot";
  botBubble.innerHTML = `
    ${botReply.replace(/\n/g, "<br>")}
    <div class="feedback" id="${feedbackId}">
        <small>Apakah jawaban ini membantu?</small>
        <button onclick="giveFeedback('${feedbackId}', true)">Membantu</button> <button onclick="giveFeedback('${feedbackId}', false)">Tidak Membantu</button>
    </div>
  `;
  log.appendChild(botBubble);
  botBubble.dataset.message = input;
  botBubble.dataset.intent = data.intent || "unknown";

  document.getElementById("message").value = "";
  log.scrollTop = log.scrollHeight;
}

function giveFeedback(id, isHelpful) {
  const div = document.getElementById(id);
  div.innerHTML = `<small>Terima kasih atas feedback-nya!</small>`;
  
  const bubble = document.getElementById(id).closest('.bot');
  const message = bubble.dataset.message;
  const intent = bubble.dataset.intent;

  fetch("/feedback", {
    method: "POST",
    headers: { "Content-Type" : "application/json"},
    body: JSON.stringify({
      message: message,
      intent: intent,
      rating: isHelpful ? "Membantu" : "Tidak Membantu"
    })
  }).then(res => res.json())
    .then(data => console.log("Feedback terkirim:", data.message))
    .catch(err => console.error("Gagal kirim feedback:", err));
}

function openMeetingPopup() {
  document.getElementById("meeting-popup").style.display = "block";
}

function closeMeetingPopup() {
  document.getElementById("meeting-popup").style.display = "none";
}

function scheduleMeeting() {
  openMeetingPopup();
}

function submitMeeting() {
  const name = document.getElementById("meeting-name").value;
  const email = document.getElementById("meeting-email").value;
  const date = document.getElementById("meeting-date").value;
  const time = document.getElementById("meeting-time").value;
  const topic = document.getElementById("meeting-topic").value;

  if (!name || !email || !date || !time || !topic) {
    alert("Mohon isi semua kolom");
    return;
  }

  fetch("/meeting", {
    method: "POST",
    headers: { "Content-Type" : "application/json"},
    body: JSON.stringify({ name, email, date, time, topic })
  })
  .then(res => res.json())
  .then(data => {
    closeMeetingPopup();
    alert("Meeting berhasil diajukan. Kami akan segera menghubungi Anda.");
  })
  .catch(err => {
    console.error("Meeting error:", err);
    alert("Terjadi kesalahan saat mengirim data meeting.");
  });
}

window.onload = () => {
  const chatlog = document.getElementById("chatlog");
  const greeting = `Hai! Saya BuddyBot. Ada yang bisa saya bantu hari ini?`;

  const greetingBubble = document.createElement("div");
  greetingBubble.className = "bot";
  greetingBubble.innerHTML = greeting;
  chatlog.appendChild(greetingBubble);
};
