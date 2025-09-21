document.addEventListener("DOMContentLoaded", function () {
  fetchMeetings();
});

function fetchMeetings() {
  fetch("/admin/meetings")
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector("#meeting-table tbody");
      tbody.innerHTML = "";
      data.forEach(item => {
        const row = `
          <tr>
            <td>${item.name}</td>
            <td>${item.email}</td>
            <td>${item.topic}</td>
            <td>${item.date || "-"}</td>
            <td>${item.time || "-"}</td>
            <td>${item.status}</td>
            <td>
              <button onclick="updateMeetingStatus(${item.id}, 'Dikonfirmasi')">Konfirmasi</button>
              <button onclick="openRescheduleModal(${item.id})">Reschedule</button>
              <button onclick="updateMeetingStatus(${item.id}, 'Ditolak')">Tolak</button>
            </td>
          </tr>
        `;
        tbody.innerHTML += row;
      });
    });
}

function updateMeetingStatus(id, status, date = null, time = null) {
  const payload = { status };
  if (date && time) {
    payload.date = date;
    payload.time = time;
  }

  fetch(`/admin/meetings/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message || "Status meeting diperbarui!");
      fetchMeetings();
    });
}

function openRescheduleModal(id) {
  document.getElementById("reschedule-id").value = id;
  document.getElementById("reschedule-modal").style.display = "flex";
}

function closeModals() {
  document.getElementById("reschedule-modal").style.display = "none";
}

document.getElementById("reschedule-form").addEventListener("submit", function (e) {
  e.preventDefault();
  const id = document.getElementById("reschedule-id").value;
  const date = document.getElementById("new-date").value;
  const time = document.getElementById("new-time").value;

  if (!date || !time) {
    alert("Mohon isi tanggal dan waktu.");
    return;
  }

  updateMeetingStatus(id, "Dijadwalkan Ulang", date, time);
  closeModals();
});
