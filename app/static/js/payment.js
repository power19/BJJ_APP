// static/js/payment.js

// Handle RFID input for customer scanning
document.addEventListener('DOMContentLoaded', function() {
    const rfidInput = document.getElementById('rfidInput');
    const scanStatus = document.getElementById('scanStatus');
    
    if (rfidInput) {
        rfidInput.focus();
        
        rfidInput.addEventListener('input', async function() {
            const rfid = this.value;
            if (rfid.length >= 8) {
                scanStatus.textContent = 'Processing...';
                
                try {
                    const response = await fetch('/api/v1/payment/scan', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ rfid: rfid })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        scanStatus.textContent = data.detail || 'Error processing card';
                        rfidInput.value = '';
                    }
                } catch (error) {
                    console.error('Error:', error);
                    scanStatus.textContent = 'Error processing card';
                    rfidInput.value = '';
                }
            }
        });
    }
});

class PaymentManager {
    constructor() {
        this.timeLeft = 30;
        this.selectedInvoices = new Set();
        this.invoiceAmounts = {};
        this.initializeElements();
        this.setupEventListeners();
        this.startTimer();
        this.filterPaidInvoices();
    }

    initializeElements() {
        this.elements = {
            timer: document.getElementById('timer'),
            totalAmount: document.getElementById('totalAmount'),
            proceedButton: document.getElementById('proceedButton'),
            authSection: document.getElementById('authSection'),
            staffRfidInput: document.getElementById('staffRfid'),
            authStatus: document.getElementById('authStatus'),
            checkboxes: document.querySelectorAll('.invoice-checkbox'),
            customerName: document.getElementById('customerName'),
            invoicesContainer: document.querySelector('.invoice-list'),
            noInvoicesMessage: document.querySelector('.no-invoices-message'),
            sessionId: document.getElementById('sessionId')
        };

        // Debug log elements found
        console.log('Initialized elements:', {
            foundElements: {
                timer: !!this.elements.timer,
                totalAmount: !!this.elements.totalAmount,
                proceedButton: !!this.elements.proceedButton,
                authSection: !!this.elements.authSection,
                staffRfidInput: !!this.elements.staffRfidInput,
                authStatus: !!this.elements.authStatus,
                checkboxes: this.elements.checkboxes.length,
                customerName: !!this.elements.customerName
            }
        });
    }

    setupEventListeners() {
        this.elements.checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateTotal();
                console.log('Checkbox changed:', {
                    id: checkbox.id,
                    checked: checkbox.checked,
                    amount: checkbox.dataset.amount
                });
            });
        });

        if (this.elements.proceedButton) {
            this.elements.proceedButton.addEventListener('click', () => this.handleProceedClick());
        }

        if (this.elements.staffRfidInput) {
            this.elements.staffRfidInput.addEventListener('input', (e) => {
                if (e.target.value.length >= 8) {
                    this.handleStaffRfid(e);
                }
            });
            this.elements.staffRfidInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                }
            });
        }
    }

    filterPaidInvoices() {
        let hasUnpaidInvoices = false;
        let visibleInvoices = 0;

        this.elements.checkboxes.forEach(checkbox => {
            const invoiceElement = checkbox.closest('.invoice-item');
            const outstandingAmount = parseFloat(checkbox.dataset.amount || 0);

            if (outstandingAmount <= 0) {
                if (invoiceElement) {
                    invoiceElement.style.display = 'none';
                }
            } else {
                hasUnpaidInvoices = true;
                visibleInvoices++;
            }
        });

        if (!hasUnpaidInvoices && this.elements.invoicesContainer) {
            this.elements.invoicesContainer.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No Outstanding Invoices</h3>
                    <p class="mt-1 text-sm text-gray-500">All invoices have been paid.</p>
                    <div class="mt-6">
                        <a href="/api/v1/payment" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                            Return to Scanner
                        </a>
                    </div>
                </div>
            `;
            if (this.elements.proceedButton) {
                this.elements.proceedButton.style.display = 'none';
            }
        }

        console.log(`Visible invoices: ${visibleInvoices}`);
    }

    updateTotal() {
        let total = 0;
        this.selectedInvoices.clear();
        this.invoiceAmounts = {};

        this.elements.checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                const amount = parseFloat(checkbox.dataset.amount || 0);
                if (!isNaN(amount)) {
                    total += amount;
                    this.selectedInvoices.add(checkbox.value);
                    this.invoiceAmounts[checkbox.value] = amount;
                }
            }
        });

        console.log('Updated totals:', {
            total: total,
            selectedInvoices: Array.from(this.selectedInvoices),
            invoiceAmounts: this.invoiceAmounts
        });

        if (this.elements.totalAmount) {
            this.elements.totalAmount.textContent = total.toFixed(2);
        }
        
        if (this.elements.proceedButton) {
            this.elements.proceedButton.disabled = this.selectedInvoices.size === 0;
        }
    }

    handleProceedClick() {
        if (this.selectedInvoices.size > 0) {
            if (this.elements.authSection) {
                this.elements.authSection.style.display = 'block';
            }
            if (this.elements.staffRfidInput) {
                this.elements.staffRfidInput.focus();
            }
            if (this.elements.proceedButton) {
                this.elements.proceedButton.style.display = 'none';
            }
        }
    }
    async handleStaffRfid(event) {
        const rfid = event.target.value;
        try {
            // Validate invoice selection first
            if (this.selectedInvoices.size === 0) {
                throw new Error('Please select at least one invoice to pay');
            }

            const total = parseFloat(this.elements.totalAmount.textContent);
            if (isNaN(total) || total <= 0) {
                throw new Error('Invalid payment amount');
            }

            this.updateAuthStatus('Verifying staff card...', 'verifying');

            // First authorize staff
            const authResponse = await fetch('/api/v1/payment/authorize-staff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    staff_rfid: rfid,
                    invoices: Array.from(this.selectedInvoices)
                })
            });

            const authData = await authResponse.json();
            console.log('Staff authorization response:', authData);

            if (!authResponse.ok) {
                throw new Error(authData.detail || 'Staff authorization failed');
            }

            this.updateAuthStatus('Staff authorized! Processing payment...', 'success');

            // Only proceed with payment if authorization was successful
            if (authData.authorized) {
                const paymentData = {
                    invoices: Array.from(this.selectedInvoices),
                    invoice_amounts: this.invoiceAmounts,
                    total_amount: total,
                    customer_name: this.elements.customerName.value,
                    staff_rfid: rfid  // Include the authorized staff RFID
                };

                console.log('Payment request data:', paymentData);

                const paymentResponse = await fetch('/api/v1/payment/process-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(paymentData)
                });

                const responseData = await paymentResponse.json();
                console.log('Payment response:', responseData);

                if (!paymentResponse.ok) {
                    throw new Error(responseData.detail || 'Payment processing failed');
                }

                // Hide paid invoices
                this.selectedInvoices.forEach(invoiceId => {
                    const checkbox = document.querySelector(`[value="${invoiceId}"]`);
                    if (checkbox) {
                        const invoiceElement = checkbox.closest('.invoice-item');
                        if (invoiceElement) {
                            invoiceElement.style.display = 'none';
                        }
                    }
                });

                this.filterPaidInvoices();

                // Redirect to success page
                window.location.href = `/api/v1/payment/success/${responseData.payment_id}`;
            } else {
                throw new Error('Staff authorization not confirmed');
            }

        } catch (error) {
            console.error('Payment Error:', error);
            this.handleAuthError(error.message);
        }

        // Clear RFID input
        event.target.value = '';
    }

    updateAuthStatus(message, status) {
        if (this.elements.authStatus) {
            this.elements.authStatus.textContent = message;
            this.elements.authStatus.className = `status-${status}`;
        }
    }

    handleAuthError(message = 'Authorization failed. Please try again.') {
        this.updateAuthStatus(message, 'error');
        
        if (this.elements.staffRfidInput) {
            this.elements.staffRfidInput.value = '';
            this.elements.staffRfidInput.focus();
        }
        
        if (this.elements.proceedButton) {
            this.elements.proceedButton.style.display = 'block';
        }
        
        setTimeout(() => {
            this.updateAuthStatus('Waiting for staff card...', 'waiting');
        }, 3000);
    }

    handleProceedClick() {
        // Check if any invoices are selected
        if (this.selectedInvoices.size === 0) {
            alert('Please select at least one invoice to pay');
            return;
        }

        // Validate total amount
        const total = parseFloat(this.elements.totalAmount.textContent);
        if (isNaN(total) || total <= 0) {
            alert('Invalid payment amount');
            return;
        }

        if (this.elements.authSection) {
            this.elements.authSection.style.display = 'block';
        }
        if (this.elements.staffRfidInput) {
            this.elements.staffRfidInput.focus();
        }
        if (this.elements.proceedButton) {
            this.elements.proceedButton.style.display = 'none';
        }
    }

    startTimer() {
        const timer = setInterval(() => {
            this.timeLeft--;
            if (this.elements.timer) {
                this.elements.timer.textContent = this.timeLeft + 's';
            }
            
            if (this.timeLeft <= 0) {
                clearInterval(timer);
                window.location.href = '/api/v1/payment';
            }
        }, 1000);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'SRD'
        }).format(amount);
    }
}

// Initialize payment manager when on invoice selection page
if (document.querySelector('.invoice-checkbox')) {
    new PaymentManager();
}