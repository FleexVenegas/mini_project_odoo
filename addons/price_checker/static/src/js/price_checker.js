/**
 * Price Checker JavaScript
 * Manejo de interacciones de la interfaz - JavaScript Vanilla
 */

(function () {
  "use strict";

  // Variables globales
  let priceCheckerInitialized = false;
  let validationMessage = null;

  /**
   * Inicializa la interfaz del price checker
   */
  function initializePriceCheckerInterface() {
    if (priceCheckerInitialized) return;

    const container = document.querySelector(".o_pricechecker");
    if (!container) return;

    bindEvents();
    focusAndSelectInput();
    priceCheckerInitialized = true;

    // Múltiples intentos para asegurar que funcione
    setTimeout(focusAndSelectInput, 50);
    setTimeout(focusAndSelectInput, 200);
    setTimeout(focusAndSelectInput, 500);
    setTimeout(focusAndSelectInput, 1000);
  }

  /**
   * Enfoca y selecciona el texto del input
   */
  function focusAndSelectInput() {
    const input = document.querySelector(".search-input");

    if (input && input.value && input.value.trim() !== "") {
      // Forzar foco
      input.focus();

      // Múltiples intentos de selección
      setTimeout(function () {
        if (input.setSelectionRange) {
          input.setSelectionRange(0, input.value.length);
        }
      }, 10);

      setTimeout(function () {
        if (input.select) {
          input.select();
        }
      }, 50);

      setTimeout(function () {
        if (input.setSelectionRange) {
          input.setSelectionRange(0, input.value.length);
        }
      }, 100);
    }
  }

  /**
   * Vincula eventos de la interfaz
   */
  function bindEvents() {
    const form = document.querySelector(".search-form");
    const input = document.querySelector(".search-input");

    if (!form || !input) return;

    // Evento para el formulario de búsqueda
    form.addEventListener("submit", function (e) {
      const query = input.value.trim();

      if (!query) {
        e.preventDefault();
        input.focus();
        showValidationMessage("Por favor ingrese un término de búsqueda");
        return false;
      }

      // Mostrar indicador de carga
      showLoadingState(true);
    });

    // Evento para limpiar mensajes de validación al escribir
    input.addEventListener("input", function () {
      hideValidationMessage();
    });

    // Evento para tecla Enter
    input.addEventListener("keypress", function (e) {
      if (e.which === 13) {
        form.submit();
      }
    });

    // Evento para hacer clic en el input (seleccionar todo cuando se hace clic)
    input.addEventListener("click", function () {
      if (input.value && input.value.trim() !== "") {
        setTimeout(function () {
          input.setSelectionRange(0, input.value.length);
        }, 10);
      }
    });

    // Evento cuando el input recibe foco
    input.addEventListener("focus", function () {
      if (input.value && input.value.trim() !== "") {
        setTimeout(function () {
          input.setSelectionRange(0, input.value.length);
        }, 10);
      }
    });

    // Evento para atajos de teclado
    input.addEventListener("keydown", function (e) {
      // Ctrl+A o Cmd+A para seleccionar todo
      if ((e.ctrlKey || e.metaKey) && e.key === "a") {
        e.preventDefault();
        input.setSelectionRange(0, input.value.length);
      }
    });
  }

  /**
   * Muestra un mensaje de validación
   */
  function showValidationMessage(message) {
    hideValidationMessage();

    const container = document.querySelector(".search-container");
    if (!container) return;

    validationMessage = document.createElement("div");
    validationMessage.className = "validation-message";
    validationMessage.textContent = message;
    validationMessage.style.cssText = `
      color: #dc2626;
      font-size: 14px;
      margin-top: 8px;
      text-align: center;
    `;

    container.appendChild(validationMessage);
  }

  /**
   * Oculta mensajes de validación
   */
  function hideValidationMessage() {
    if (validationMessage && validationMessage.parentNode) {
      validationMessage.parentNode.removeChild(validationMessage);
      validationMessage = null;
    }
  }

  /**
   * Muestra/oculta estado de carga
   */
  function showLoadingState(show) {
    const btn = document.querySelector(".search-btn");
    if (!btn) return;

    if (show) {
      btn.disabled = true;
      btn.textContent = "Buscando...";
      btn.style.opacity = "0.7";
    } else {
      btn.disabled = false;
      btn.textContent = "Consultar";
      btn.style.opacity = "1";
    }
  }

  // Inicializar cuando el DOM esté listo
  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initializePriceCheckerInterface
    );
  } else {
    initializePriceCheckerInterface();
  }

  // También en window load por si acaso
  window.addEventListener("load", function () {
    setTimeout(initializePriceCheckerInterface, 100);
  });
})();

// Funciones adicionales para asegurar la selección
(function () {
  "use strict";

  // Función simple para auto-selección que se ejecuta repetidamente
  function autoSelectText() {
    const input = document.querySelector(".search-input");
    if (
      input &&
      input.value &&
      input.value.trim() !== "" &&
      document.body.contains(input) &&
      input.offsetParent !== null
    ) {
      // Solo si el input es visible y tiene contenido
      try {
        input.focus();
        input.setSelectionRange(0, input.value.length);
      } catch (e) {
        // Fallback silencioso
        try {
          input.select();
        } catch (e2) {
          // Ignore errors
        }
      }
    }
  }

  // Ejecutar auto-selección con diferentes intervalos
  setTimeout(autoSelectText, 100);
  setTimeout(autoSelectText, 300);
  setTimeout(autoSelectText, 600);
  setTimeout(autoSelectText, 1000);

  // Evento que se ejecuta cada vez que se muestra la página
  window.addEventListener("pageshow", function () {
    setTimeout(autoSelectText, 100);
  });

  // Observer para detectar cambios en el DOM
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
        setTimeout(autoSelectText, 100);
      }
    });
  });

  // Observar cambios en el body cuando esté disponible
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    });
  }
})();
