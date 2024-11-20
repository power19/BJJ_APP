// Store recent searches in localStorage
const RECENT_SEARCHES_KEY = 'recentCustomerSearches';
const MAX_RECENT_SEARCHES = 5;

// Initialize recent searches
let recentSearches = JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || '[]');

// Update recent searches display
function updateRecentSearches() {
    const container = document.getElementById('recentSearches');
    if (!container) return;
    
    container.innerHTML = recentSearches.map(customer => `
        <div class="customer-card bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:shadow-md">
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-semibold text-lg">${customer.name}</h3>
                    <p class="text-sm text-gray-600">${customer.email || 'No email'}</p>
                </div>
                <div class="flex space-x-2">
                    <a href="/api/v1/attendance/customer/${encodeURIComponent(customer.name)}" 
                       class="px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                        Attendance
                    </a>
                    <a href="/api/v1/billing/customer/${encodeURIComponent(customer.name)}" 
                       class="px-3 py-1 text-sm bg-green-50 text-green-600 rounded hover:bg-green-100">
                        Billing
                    </a>
                </div>
            </div>
        </div>
    `).join('');
}

// Select customer from search results
function selectCustomer(name, email) {
    console.log(`Selecting customer: ${name}`); // Debug log
    document.getElementById('searchInput').value = name;
    document.getElementById('searchResults').style.display = 'none';
    addToRecentSearches({ name, email });
    
    // Updated URLs to match FastAPI routes
    const billingUrl = `/api/v1/billing/customer/${encodeURIComponent(name)}`;
    const attendanceUrl = `/api/v1/attendance/customer/${encodeURIComponent(name)}`;
    
    console.log(`Generated billing URL: ${billingUrl}`); // Debug log
    
    // Show customer actions
    const actionsContainer = document.getElementById('customerActions');
    actionsContainer.innerHTML = `
        <div class="flex justify-center space-x-4 mt-4">
            <a href="${attendanceUrl}" 
               class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
               onclick="console.log('Clicking attendance link:', this.href)">
                View Attendance
            </a>
            <a href="${billingUrl}" 
               class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
               onclick="console.log('Clicking billing link:', this.href)">
                View Billing
            </a>
        </div>
    `;
    actionsContainer.style.display = 'block';
}


// Add to recent searches
function addToRecentSearches(customer) {
    recentSearches = [customer, ...recentSearches.filter(c => c.name !== customer.name)]
        .slice(0, MAX_RECENT_SEARCHES);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recentSearches));
    updateRecentSearches();
}

// Search customers
async function searchCustomers(query) {
    if (!query) {
        document.getElementById('searchResults').style.display = 'none';
        return;
    }

    console.log('Searching for:', query);
    document.getElementById('loadingSpinner').style.display = 'block';
    
    try {
        const response = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Search results:', data);
        
        const resultsDiv = document.getElementById('searchResults');
        if (data.length === 0) {
            resultsDiv.innerHTML = `
                <div class="p-3 text-gray-500">
                    No customers found matching "${query}"
                </div>
            `;
        } else {
            resultsDiv.innerHTML = data.map(customer => `
                <div class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0" 
                     onclick="selectCustomer('${customer.name}', '${customer.email || ''}')">
                    <div class="font-medium">${customer.name}</div>
                    <div class="text-sm text-gray-600">${customer.email || 'No email'}</div>
                </div>
            `).join('');
        }
        
        resultsDiv.style.display = 'block';
    } catch (error) {
        console.error('Search failed:', error);
        const resultsDiv = document.getElementById('searchResults');
        resultsDiv.innerHTML = `
            <div class="p-3 text-red-500">
                Error performing search. Please try again.
            </div>
        `;
        resultsDiv.style.display = 'block';
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const debouncedSearch = debounce(searchCustomers, 300);
    
    // Handle form submission
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query) {
            searchCustomers(query);
        }
    });
    
    // Handle input changes for real-time search
    searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value));
    
    updateRecentSearches();
    
    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            document.getElementById('searchResults').style.display = 'none';
        }
    });
});

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}