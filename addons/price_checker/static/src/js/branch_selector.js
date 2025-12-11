/**
 * Branch Selector JavaScript
 * Manejo de selección de sucursal y localStorage
 */

(function () {
  "use strict";

  const STORAGE_KEY = "price_checker_warehouse_id";
  const STORAGE_NAME_KEY = "price_checker_warehouse_name";

  /**
   * Inicializa el selector de sucursal
   */
  function initializeBranchSelector() {
    const branchSelector = document.querySelector(".o_branch_selector");
    if (!branchSelector) return;

    // Verificar si hay una sucursal guardada
    const savedWarehouseId = localStorage.getItem(STORAGE_KEY);

    // Si hay una sucursal guardada, mostrar mensaje
    if (savedWarehouseId) {
      showSavedBranchMessage(savedWarehouseId);
    }

    // Bind eventos a los botones de selección
    const selectButtons = document.querySelectorAll(".branch-select-btn");
    selectButtons.forEach(function (button) {
      button.addEventListener("click", handleBranchSelection);
    });

    // También permitir clic en toda la tarjeta
    const branchCards = document.querySelectorAll(".branch-card");
    branchCards.forEach(function (card) {
      card.addEventListener("click", function (e) {
        // Solo si no se hizo clic directamente en el botón
        if (!e.target.classList.contains("branch-select-btn")) {
          const button = card.querySelector(".branch-select-btn");
          if (button) {
            button.click();
          }
        }
      });

      // Añadir efecto hover
      card.style.cursor = "pointer";
    });
  }

  /**
   * Maneja la selección de sucursal
   */
  function handleBranchSelection(e) {
    const button = e.currentTarget;
    const warehouseId = button.getAttribute("data-warehouse-id");
    const warehouseName = button.getAttribute("data-warehouse-name");

    if (!warehouseId) {
    //   console.error("No se pudo obtener el warehouse_id");
      return;
    }

    // Guardar en localStorage
    localStorage.setItem(STORAGE_KEY, warehouseId);
    localStorage.setItem(STORAGE_NAME_KEY, warehouseName);

    // console.log(`Sucursal seleccionada: ${warehouseName} (ID: ${warehouseId})`);

    // Mostrar feedback visual
    button.textContent = "Cargando...";
    button.disabled = true;

    // Redirigir al checador de precios con el warehouse_id
    window.location.href = `/price-checker/branch?warehouse_id=${warehouseId}`;
  }

  /**
   * Muestra mensaje de sucursal guardada
   */
  function showSavedBranchMessage(warehouseId) {
    const warehouseName = localStorage.getItem(STORAGE_NAME_KEY);
    const header = document.querySelector(".branch-selector-header");

    if (!header) return;

    const messageDiv = document.createElement("div");
    messageDiv.className = "saved-branch-message";
    messageDiv.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>Última sucursal: <strong>${
        warehouseName || "Sucursal #" + warehouseId
      }</strong></span>
    `;

    header.appendChild(messageDiv);
  }

  /**
   * Inicializa el checador de precios con manejo de localStorage
   */
  function initializePriceChecker() {
    const priceChecker = document.querySelector(".o_pricechecker");
    if (!priceChecker) return;

    // Obtener warehouse_id de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const warehouseId = urlParams.get("warehouse_id");

    // Si hay warehouse_id, actualizarlo en localStorage
    if (warehouseId) {
      localStorage.setItem(STORAGE_KEY, warehouseId);

      // Intentar obtener el nombre del warehouse del DOM
      const warehouseNameElement = document.querySelector(".warehouse-name");
      if (warehouseNameElement) {
        const warehouseName = warehouseNameElement.textContent.trim();
        localStorage.setItem(STORAGE_NAME_KEY, warehouseName);
      }
    } else {
      // Si no hay warehouse_id en la URL, verificar localStorage
      const savedWarehouseId = localStorage.getItem(STORAGE_KEY);
      if (savedWarehouseId) {
        // Redirigir con el warehouse_id guardado
        const currentQuery = urlParams.get("query") || "";
        const newUrl = `/price-checker/branch?warehouse_id=${savedWarehouseId}${
          currentQuery ? "&query=" + encodeURIComponent(currentQuery) : ""
        }`;
        window.location.href = newUrl;
        return;
      }
    }
  }

  /**
   * Inicialización al cargar el DOM
   */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    initializeBranchSelector();
    initializePriceChecker();
  }
})();
