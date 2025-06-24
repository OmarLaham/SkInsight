document.addEventListener("DOMContentLoaded", function () {
    // Your entire script goes here...
    
    // Professionals & Clients
    const rowsPerPage = 5;


    // ==============================================================
    // Professiaonals
    // ==============================================================
    let professionalsCurrentPage = 1;

    const practitionersTableData = JSON.parse(document.getElementById("practitioners-tbl-data").textContent); // practioners_tbl_data is populated in the template using context 
    let practitionersFilteredData = [...practitionersTableData];
  
    const professionalsDataBody = document.getElementById("professionalsDataBody");
    const professionalsSearchInput = document.getElementById("professionalsSearchInput");
    const professionalsPaginationPrevBtn = document.getElementById("professionalsPaginationPrevBtn");
    const professionalsPaginationNextBtn = document.getElementById("professionalsPaginationNextBtn");
  
    function professionalsRenderTable(data, page = 1) {
      professionalsDataBody.innerHTML = "";
      const start = (page - 1) * rowsPerPage;
      const paginated = data.slice(start, start + rowsPerPage);
      for (const row of paginated) {
        professionalsDataBody.innerHTML += `
          <tr class="hover:bg-gray-50">
            <td class="px-6 py-4">${row.title + " " + row.first_name + " " + row.last_name}<br />(<a href="/professional/edit/${row.practitioner_id}"><button class="text-pink-600 hover:underline">تعديل البيانات</button></a>)</td>
            <td class="px-6 py-4">${row.gender}</td>
            <td class="px-6 py-4">${row.organization_name}</td>
            <td class="px-6 py-4">${row.organization_city}</td>
            <td class="px-6 py-4">${row.organization_country}</td>
            <td class="px-6 py-4">${row.active}</td>
            <td class="px-6 py-4 space-x-2 rtl:space-x-reverse text-center">
              <a href="/professional/subscribe/${row.practitioner_id}"><button class="text-pink-600 hover:underline">Manage Subscription</button></a><span class="text-gray-300">|</span>
              <a href="/professional/clients-plan/${row.practitioner_id}"><button class="text-pink-600 hover:underline">Clients Plan</button></a><span class="text-gray-300">|</span>
              <a href="/professional/deactivate/${row.practitioner_id}"><button class="text-pink-600 hover:underline">Deacivate Account</button></a><span class="text-gray-300">|</span>
              <a href="/professional/activate/${row.practitioner_id}"><button class="text-pink-600 hover:underline">Activate Account</button></a>
            </td>
          </tr>`;
      }
    }
  
    function professionalsUpdatePagination(data) {
      professionalsPaginationPrevBtn.disabled = professionalsCurrentPage === 1;
      professionalsPaginationNextBtn.disabled = professionalsCurrentPage * rowsPerPage >= data.length;
    }
  
    function professionalsFilterData() {
      const keyword = professionalsSearchInput.value.trim().toLowerCase();
      practitionersFilteredData = practitionersTableData.filter(entry =>
        entry.first_name.toLowerCase().includes(keyword) || entry.last_name.toLowerCase().includes(keyword) || entry.organization_name.toLowerCase().includes(keyword)
      );
      professionalsCurrentPage = 1;
      professionalsRenderTable(practitionersFilteredData, professionalsCurrentPage);
      professionalsUpdatePagination(practitionersFilteredData);
    }
  
    // Initial Render
    professionalsRenderTable(practitionersFilteredData, professionalsCurrentPage);
    professionalsUpdatePagination(practitionersFilteredData);
  
    // Event Listeners
    professionalsSearchInput.addEventListener("input", professionalsFilterData);
  
    professionalsPaginationPrevBtn.addEventListener("click", () => {
      if (professionalsCurrentPage > 1) {
        professionalsCurrentPage--;
        professionalsRenderTable(practitionersFilteredData, professionalsCurrentPage);
        professionalsUpdatePagination(practitionersFilteredData);
      }
    });
  
    professionalsPaginationNextBtn.addEventListener("click", () => {
      if (professionalsCurrentPage * rowsPerPage < practitionersFilteredData.length) {
        professionalsCurrentPage++;
        professionalsRenderTable(practitionersFilteredData, professionalsCurrentPage);
        professionalsUpdatePagination(practitionersFilteredData);
      }
    });
 

    // ==============================================================
    // Clients
    // ==============================================================

    let clientsCurrentPage = 1;
    
    const clients = JSON.parse(document.getElementById("clients-tbl-data").textContent); // clients_tbl_data is populated in the template using context 
    let clientsFilteredData = [...clients]; // assign initial data here

    const clientsDataBody = document.getElementById("clientsDataBody");
    const clientsSearchInput = document.getElementById("clientsSearchInput");
    const clientsPaginationPrevBtn = document.getElementById("clientsPaginationPrevBtn");
    const clientsPaginationNextBtn = document.getElementById("clientsPaginationNextBtn");

    function clientsRenderTable(data, page = 1) {
      clientsDataBody.innerHTML = "";
      const start = (page - 1) * rowsPerPage;
      const paginated = data.slice(start, start + rowsPerPage);
      for (const row of paginated) {
        clientsDataBody.innerHTML += `
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
              <a href="/client/deactivate/${row.patient_id}"><button class="text-pink-600 hover:underline">Deacivate Account</button></a><span class="text-gray-300">|</span>
              <a href="/client/activate/${row.patient_id}"><button class="text-pink-600 hover:underline">Activate Account</button></a>
            </td>
          </tr>`;
      }
    }

    function clientsUpdatePagination(data) {
      clientsPaginationPrevBtn.disabled = clientsCurrentPage === 1;
      clientsPaginationNextBtn.disabled = clientsCurrentPage * rowsPerPage >= data.length;
    }

    function clientsFilterData() {
      const keyword = clientsSearchInput.value.trim().toLowerCase();
      clientsFilteredData = clients.filter(client =>
        client.full_name.toLowerCase().includes(keyword) || client.birth_date.toLowerCase().includes(keyword)
      );
      clientsCurrentPage = 1;
      clientsRenderTable(clientsFilteredData, clientsCurrentPage);
      clientsUpdatePagination(clientsFilteredData);
    }

    // Initial Render
    clientsRenderTable(clientsFilteredData, clientsCurrentPage);
    clientsUpdatePagination(clientsFilteredData);

    // Event Listeners
    clientsSearchInput.addEventListener("input", clientsFilterData);

    clientsPaginationPrevBtn.addEventListener("click", () => {
      if (clientsCurrentPage > 1) {
        clientsCurrentPage--;
        clientsRenderTable(clientsFilteredData, clientsCurrentPage);
        clientsUpdatePagination(clientsFilteredData);
      }
    });

    clientsPaginationNextBtn.addEventListener("click", () => {
      if (clientsCurrentPage * rowsPerPage < clientsFilteredData.length) {
        clientsCurrentPage++;
        clientsRenderTable(clientsFilteredData, clientsCurrentPage);
        clientsUpdatePagination(clientsFilteredData);
      }
    });

  });