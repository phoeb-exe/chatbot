document.addEventListener("DOMContentLoaded", function () {
  loadSummary();
  loadIntentStats();
  loadMeetingReport();
  loadFeedbackReport();
});

function loadSummary() {
  fetch("/admin/api/chatbot-summary")
    .then(res => res.json())
    .then(data => {
      document.getElementById("total-pertanyaan").textContent = data.total_pertanyaan;
      document.getElementById("terjawab").textContent = data.terjawab;
      document.getElementById("tidak-terjawab").textContent = data.tidak_terjawab;
      document.getElementById("intent-populer").textContent = data.intent_populer;
      document.getElementById("jumlah-populer").textContent = data.jumlah_populer;
      document.getElementById("feedback-positif").textContent = data.feedback_positif;
    });
}

function loadIntentStats() {
  fetch("/admin/api/intent-statistics")
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById("intent-table");
      tbody.innerHTML = "";

      data.forEach(row => {
        const positif = parseInt(row.positif || 0);
        const total = parseInt(row.jumlah || 1);
        const persen = Math.round((positif / total) * 100);

        tbody.innerHTML += `
          <tr>
            <td>${row.intent}</td>
            <td>${row.jumlah}</td>
            <td>${persen}%</td>
          </tr>`;
      });
    });
}

function loadMeetingReport() {
  fetch("/admin/api/meeting-report")
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById("meeting-table");
      tbody.innerHTML = "";
      data.forEach(row => {
        tbody.innerHTML += `
          <tr>
            <td>${row.name}</td>
            <td>${row.topic}</td>
            <td>${row.date}</td>
            <td>${row.time}</td>
            <td>${row.status}</td>
          </tr>`;
      });
    });
}

function loadFeedbackReport() {
  fetch("/admin/api/feedback-report")
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById("feedback-table");
      tbody.innerHTML = "";
      data.forEach(row => {
        tbody.innerHTML += `
          <tr>
            <td>${row.message}</td>
            <td>${row.intent}</td>
            <td>${row.rating}</td>
            <td>${row.date}</td>
          </tr>`;
      });
    });
}

function exportPDF(type) {
  window.open(`/admin/export/${type}`, '_blank');
}
