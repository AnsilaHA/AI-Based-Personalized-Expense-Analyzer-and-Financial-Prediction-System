// Main JavaScript utilities

document.addEventListener("DOMContentLoaded", function () {
    // 1. Sidebar Toggler
    const sidebarCollapse = document.getElementById("sidebarCollapse");
    const sidebar = document.getElementById("sidebar");
    
    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener("click", function () {
            sidebar.classList.toggle("active");
        });
    }

    // 2. Dark/Light Mode Theme Toggle
    const themeToggle = document.getElementById("themeToggle");
    const body = document.body;
    
    // Check local storage for theme preference
    if (localStorage.getItem("theme") === "dark") {
        body.classList.add("dark-theme");
        if (themeToggle) {
            themeToggle.innerHTML = '<i class="bi bi-sun-fill"></i>';
        }
    } else {
        body.classList.remove("dark-theme");
        if (themeToggle) {
            themeToggle.innerHTML = '<i class="bi bi-moon-fill"></i>';
        }
    }
    
    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            body.classList.toggle("dark-theme");
            
            if (body.classList.contains("dark-theme")) {
                localStorage.setItem("theme", "dark");
                themeToggle.innerHTML = '<i class="bi bi-sun-fill"></i>';
            } else {
                localStorage.setItem("theme", "light");
                themeToggle.innerHTML = '<i class="bi bi-moon-fill"></i>';
            }
        });
    }
});

// 3. Edit Transaction Modal Helper
// Pre-fills editing modal values dynamically from table row data
function prepareEditModal(txId, type, catId, amount, date, desc, freq, isRec) {
    const formAction = `/transactions/edit/${txId}`;
    const modalForm = document.getElementById("editTransactionForm");
    if (modalForm) {
        modalForm.setAttribute("action", formAction);
    }
    
    const typeSelect = document.getElementById("edit_type");
    if (typeSelect) {
        typeSelect.value = type;
        // Trigger change event to filter categories dropdown in edit modal
        filterEditCategories(type);
    }
    
    const catSelect = document.getElementById("edit_category_id");
    if (catSelect) {
        catSelect.value = catId;
    }
    
    const amountInput = document.getElementById("edit_amount");
    if (amountInput) {
        amountInput.value = amount;
    }
    
    const dateInput = document.getElementById("edit_date");
    if (dateInput) {
        dateInput.value = date;
    }
    
    const descInput = document.getElementById("edit_description");
    if (descInput) {
        descInput.value = desc;
    }
    
    const freqSelect = document.getElementById("edit_frequency");
    if (freqSelect) {
        freqSelect.value = freq;
    }
    
    const recInput = document.getElementById("edit_is_recurring");
    if (recInput) {
        recInput.value = isRec;
    }
}

// Category filter based on Type select in Add/Edit Modals
function filterCategories(type) {
    const catSelect = document.getElementById("add_category_id");
    if (!catSelect) return;
    
    const options = catSelect.options;
    let firstVisibleIndex = -1;
    
    for (let i = 0; i < options.length; i++) {
        const option = options[i];
        const optType = option.getAttribute("data-type");
        
        if (optType === type) {
            option.style.display = "block";
            if (firstVisibleIndex === -1) {
                firstVisibleIndex = i;
            }
        } else {
            option.style.display = "none";
        }
    }
    
    if (firstVisibleIndex !== -1) {
        catSelect.selectedIndex = firstVisibleIndex;
    }
}

function filterEditCategories(type) {
    const catSelect = document.getElementById("edit_category_id");
    if (!catSelect) return;
    
    const options = catSelect.options;
    let firstVisibleIndex = -1;
    
    for (let i = 0; i < options.length; i++) {
        const option = options[i];
        const optType = option.getAttribute("data-type");
        
        if (optType === type) {
            option.style.display = "block";
            if (firstVisibleIndex === -1) {
                firstVisibleIndex = i;
            }
        } else {
            option.style.display = "none";
        }
    }
}
