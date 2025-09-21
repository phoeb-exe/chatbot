document.addEventListener("DOMContentLoaded", function () {
  fetchQuestions();
  fetchAnswers();
});


function fetchQuestions() {
  fetch("/admin/qa")
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector("#question-table tbody");
      tbody.innerHTML = "";
      data.forEach(item => {
        const row = `
          <tr>
            <td>${item.id}</td>
            <td>${item.komentar}</td>
            <td>${item.label_intent}</td>
            <td>
              <button onclick="editQA(${item.id}, '${item.komentar}', '${item.label_intent}', \`${item.jawaban}\`)">Edit</button>
              <button onclick="deleteQA(${item.id})">Hapus</button>
            </td>
          </tr>
        `;
        tbody.innerHTML += row;
      });

      // Dropdown label intent
      const intents = [...new Set(data.map(item => item.label_intent))];
      const select = document.getElementById("intent-select");
      select.innerHTML = `<option value="">Pilih Intent</option>`;
      intents.forEach(intent => {
        select.innerHTML += `<option value="${intent}">${intent}</option>`;
      });
    });
}


function fetchAnswers() {
  fetch("/admin/answers")
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector("#answer-table tbody");
      tbody.innerHTML = "";
      data.forEach(item => {
        const row = `
          <tr>
            <td>${item.label_intent}</td>
            <td>${item.jawaban}</td>
            <td>
              <button onclick="editAnswer('${item.label_intent}', \`${item.jawaban}\`)">Edit</button>
              <button onclick="deleteAnswer('${item.label_intent}')">Hapus</button>
            </td>
          </tr>
        `;
        tbody.innerHTML += row;
      });
    });
}


function openQuestionModal() {
  document.getElementById("question-modal").style.display = "flex";
  document.getElementById("question-form").reset();
  document.getElementById("qa-id").value = "";
}

function openAnswerModal() {
  document.getElementById("answer-modal").style.display = "flex";
  document.getElementById("answer-form").reset();
  document.getElementById("answer-mode").value = "add";
}

function closeModals() {
  document.querySelectorAll(".modal").forEach(m => m.style.display = "none");
}


document.getElementById("question-form").addEventListener("submit", function (e) {
  e.preventDefault();
  const id = document.getElementById("qa-id").value;
  const komentar = document.getElementById("qa-question").value;
  const label_intent = document.getElementById("intent-select").value;

  if (!komentar || !label_intent) return alert("Isi semua field!");

  fetch("/admin/answers")
    .then(res => res.json())
    .then(data => {
      const jawaban = data.find(d => d.label_intent === label_intent)?.jawaban || "Belum ada jawaban.";

      const method = id ? "PUT" : "POST";
      const url = id ? `/admin/qa/${id}` : "/admin/qa";

      fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ komentar, label_intent, jawaban })
      })
        .then(res => res.json())
        .then(data => {
          alert(data.message || "Berhasil disimpan!");
          closeModals();
          fetchQuestions();
        });
    });
});

document.getElementById("answer-form").addEventListener("submit", function (e) {
  e.preventDefault();
  const label_intent = document.getElementById("answer-intent").value;
  const jawaban = document.getElementById("answer-text").value;
  const mode = document.getElementById("answer-mode").value;

  const url = mode === "edit" ? `/admin/answers/${label_intent}` : "/admin/qa";
  const method = mode === "edit" ? "PUT" : "POST";
  const body = mode === "edit"
    ? JSON.stringify({ jawaban })
    : JSON.stringify({ komentar: "-", label_intent, jawaban });

  fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message || (mode === "edit" ? "Jawaban diperbarui." : "Jawaban ditambahkan."));
      closeModals();
      fetchAnswers();
      fetchQuestions();
    });
});


function deleteQA(id) {
  if (confirm("Hapus pertanyaan ini?")) {
    fetch(`/admin/qa/${id}`, { method: "DELETE" })
      .then(res => res.json())
      .then(data => {
        alert(data.message || "Pertanyaan berhasil dihapus.");
        fetchQuestions();
      });
  }
}

function deleteAnswer(intent) {
  if (confirm("Hapus semua jawaban dengan intent ini?")) {
    fetch(`/admin/answers/${intent}`, { method: "DELETE" })
      .then(res => res.json())
      .then(data => {
        alert(data.message || "Jawaban berhasil dihapus.");
        fetchAnswers();
        fetchQuestions();
      });
  }
}

function editQA(id, komentar, label_intent, jawaban) {
  openQuestionModal();
  document.getElementById("qa-id").value = id;
  document.getElementById("qa-question").value = komentar;
  document.getElementById("intent-select").value = label_intent;
}

function editAnswer(label_intent, jawaban) {
  openAnswerModal();
  document.getElementById("answer-mode").value = "edit";
  document.getElementById("answer-intent").value = label_intent;
  document.getElementById("answer-text").value = jawaban;
}
