document.addEventListener('DOMContentLoaded', function() {
    const fetchBillingInfo = async (customerId) => {
        try {
            const response = await fetch(`/api/v1/billing/${customerId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching billing info:', error);
        }
    };
});
