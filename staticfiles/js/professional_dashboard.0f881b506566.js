document.addEventListener("DOMContentLoaded", function () {
  // Your entire script goes here...

  const rowsPerPage = 5;
  let currentPage = 1;
  const clients = JSON.parse(document.getElementById("clients-tbl-data").textContent); // clients_tbl_data is populated in the template using context 
  let filteredData = [...clients]; // assign initial data here

  const dataBody = document.getElementById("dataBody");
  const searchInput = document.getElementById("searchInput");
  const paginationPrevBtn = document.getElementById("paginationPrevBtn");
  const paginationNextBtn = document.getElementById("paginationNextBtn");

  function renderTable(data, page = 1) {
    dataBody.innerHTML = "";
    const start = (page - 1) * rowsPerPage;
    const paginated = data.slice(start, start + rowsPerPage);
    for (const row of paginated) {
      dataBody.innerHTML += `
        <tr class="hover:bg-gray-50">
          <td class="px-6 py-4">
            ${row.full_name} (
              <a href="/client/edit/${row.patient_id}"><button class="text-pink-600 hover:underline">تعديل البيانات</button></a>
            )
          </td>
          <td class="px-6 py-4">${row.gender}</td>
          <td class="px-6 py-4">${row.birth_date}</td>
          <td class="px-6 py-4">${row.active}</td>
          <td class="px-6 py-4 space-x-2 rtl:space-x-reverse">
            <a href="/client/quiz-start/${row.patient_id}"><button class="text-pink-600 hover:underline">📝 اختبار جديد</button></a><span class="text-gray-300">|</span>
            <a href="/client/care-chart/${row.patient_id}"><button class="text-pink-600 hover:underline">📈 مخطط العناية</button></a><span class="text-gray-300">|</span>
            <a href="/messages/${row.whatsapp_number}"><button class="text-pink-600 hover:underline">💬 الرسائل</button></a>
          </td>
        </tr>`;
    }
  }

  function updatePagination(data) {
    paginationPrevBtn.disabled = currentPage === 1;
    paginationNextBtn.disabled = currentPage * rowsPerPage >= data.length;
  }

  function filterData() {
    const keyword = searchInput.value.trim();
    filteredData = clients.filter(client =>
      client.full_name.includes(keyword) || client.birth_date.includes(keyword)
    );
    currentPage = 1;
    renderTable(filteredData, currentPage);
    updatePagination(filteredData);
  }

  // Initial Render
  renderTable(filteredData, currentPage);
  updatePagination(filteredData);

  // Event Listeners
  searchInput.addEventListener("input", filterData);

  paginationPrevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderTable(filteredData, currentPage);
      updatePagination(filteredData);
    }
  });

  paginationNextBtn.addEventListener("click", () => {
    if (currentPage * rowsPerPage < filteredData.length) {
      currentPage++;
      renderTable(filteredData, currentPage);
      updatePagination(filteredData);
    }
  });
});
