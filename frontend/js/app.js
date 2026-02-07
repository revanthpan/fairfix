const mockAnalysis = {
  vehicle: "2018 Honda Civic",
  shopQuote: 1200,
  fairPrice: 850,
  flags: ["Overcharged Labor (2x standard)", "Unnecessary 'Engine Flush'"],
};

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const applyAnalysis = (analysis) => {
  const vehicleValue = document.querySelector("#vehicleValue");
  const shopQuoteValue = document.querySelector("#shopQuoteValue");
  const fairPriceValue = document.querySelector("#fairPriceValue");
  const flagsList = document.querySelector("#flagsList");

  vehicleValue.textContent = analysis.vehicle;
  shopQuoteValue.textContent = formatCurrency(analysis.shopQuote);
  fairPriceValue.textContent = formatCurrency(analysis.fairPrice);

  flagsList.innerHTML = "";
  analysis.flags.forEach((flag) => {
    const card = document.createElement("div");
    card.className = "flag-card";
    card.textContent = flag;
    flagsList.appendChild(card);
  });
};

const setupScriptToggle = () => {
  const scriptButton = document.querySelector("#scriptButton");
  const scriptBox = document.querySelector("#scriptBox");

  scriptButton.addEventListener("click", () => {
    const isHidden = scriptBox.style.display === "none";
    scriptBox.style.display = isHidden ? "block" : "none";
    scriptButton.textContent = isHidden
      ? "Hide Negotiation Script"
      : "Show This to Your Mechanic";
  });
};

document.addEventListener("DOMContentLoaded", () => {
  applyAnalysis(mockAnalysis);
  setupScriptToggle();
});
