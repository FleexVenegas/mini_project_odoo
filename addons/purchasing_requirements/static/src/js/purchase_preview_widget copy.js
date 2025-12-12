// /** @odoo-module **/

// (function () {
//     "use strict";

//     function safeGetRecordId() {
//         const input = document.querySelector("input[name='id']");
//         return input ? input.value : null;
//     }

//     function renderIframe() {
//         const container = document.querySelector(".purchasing-preview-container");
//         if (!container) return;

//         const recordId = safeGetRecordId();
//         if (!recordId) {
//             container.innerHTML = "<p style='padding:10px;color:#888;'>Guarda el registro para ver la vista previa</p>";
//             return;
//         }

//         container.innerHTML = `
//             <iframe
//                 src="/report/html/purchasing_requirements.report_purchasing_requirements_template/${recordId}"
//                 style="width:100%; height:100%; border:0;"
//             ></iframe>
//         `;
//     }

//     function whenFormIsReady(callback) {
//         const interval = setInterval(() => {
//             const sheet = document.querySelector(".o_form_sheet_bg"); // Formulario backend
//             if (sheet) {
//                 clearInterval(interval);
//                 callback();
//             }
//         }, 300);
//     }

//     // Esperar a que el backend Odoo cargue completamente
//     document.addEventListener("DOMContentLoaded", function () {
//         whenFormIsReady(renderIframe);
//     });

//     window.addEventListener("load", function () {
//         whenFormIsReady(renderIframe);
//     });

//     // MutationObserver seguro
//     const waitForBody = setInterval(() => {
//         if (document.body) {
//             clearInterval(waitForBody);

//             const observer = new MutationObserver(function () {
//                 whenFormIsReady(renderIframe);
//             });

//             observer.observe(document.body, {
//                 childList: true,
//                 subtree: true
//             });
//         }
//     }, 200);
// })();
    