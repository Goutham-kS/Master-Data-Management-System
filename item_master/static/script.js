// document.getElementById("search-form").addEventListener("submit", function(event) {
//     event.preventDefault();

//     const itemCodes = document.getElementById("item-codes").value.split(",");
//     const unitName = document.getElementById("unit-name").value.trim();

//     fetch("/search", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json"
//         },
//         body: JSON.stringify({ item_codes: itemCodes, unit_name: unitName })
//     })
//     .then(response => response.json())
//     .then(data => {
//         const resultsDiv = document.getElementById("results");
//         resultsDiv.innerHTML = "";

//         if (data.error) {
//             resultsDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
//             return;
//         }
        
//         if (data.message) {
//             resultsDiv.innerHTML = `<p>${data.message}</p>`;
//             return;
//         }

//         let table = "<table border='1'><tr>";
//         Object.keys(data[0]).forEach(col => {
//             table += `<th>${col}</th>`;
//         });
//         table += "</tr>";

//         data.forEach(row => {
//             table += "<tr>";
//             Object.values(row).forEach(value => {
//                 table += `<td>${value}</td>`;
//             });
//             table += "</tr>";
//         });

//         table += "</table>";
//         resultsDiv.innerHTML = table;
//     })
//     .catch(error => {
//         console.error("Error:", error);
//         document.getElementById("results").innerHTML = `<p style="color: red;">An error occurred.</p>`;
//     });
// });