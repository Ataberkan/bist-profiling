// BIST Profil Analiz Web Sitesi JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Sayfa yüklendiğinde çalışacak kodlar
    console.log('BIST Profil Analiz Web Sitesi yüklendi!');
    
    // Mobil menü toggle
    const navbarToggle = document.querySelector('.navbar-toggle');
    const navbarNav = document.querySelector('.navbar-nav');
    
    if (navbarToggle && navbarNav) {
        navbarToggle.addEventListener('click', function() {
            navbarNav.classList.toggle('show');
        });

        // Menü öğelerine tıklandığında menüyü kapat
        const navLinks = navbarNav.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navbarNav.classList.remove('show');
            });
        });

        // Sayfa dışına tıklandığında menüyü kapat
        document.addEventListener('click', function(event) {
            const isClickInside = navbarNav.contains(event.target) || navbarToggle.contains(event.target);
            if (!isClickInside && navbarNav.classList.contains('show')) {
                navbarNav.classList.remove('show');
            }
        });
    }
    
    // Tablo sıralama fonksiyonu
    const sortableTables = document.querySelectorAll('.sortable');
    
    sortableTables.forEach(function(table) {
        const headers = table.querySelectorAll('th');
        
        headers.forEach(function(header, index) {
            header.addEventListener('click', function() {
                sortTable(table, index);
            });
        });
    });
    
    // Hisse detay modalı
    const stockDetailLinks = document.querySelectorAll('.stock-detail-link');
    const stockDetailModal = document.querySelector('.stock-detail-modal');
    const closeModal = document.querySelector('.close-modal');
    
    if (stockDetailLinks && stockDetailModal) {
        stockDetailLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const stockCode = this.getAttribute('data-stock-code');
                loadStockDetails(stockCode);
                stockDetailModal.style.display = 'block';
            });
        });
        
        if (closeModal) {
            closeModal.addEventListener('click', function() {
                stockDetailModal.style.display = 'none';
            });
        }
        
        window.addEventListener('click', function(e) {
            if (e.target === stockDetailModal) {
                stockDetailModal.style.display = 'none';
            }
        });
    }
    
    // Kümeleme grafiği
    const clusterChart = document.getElementById('clusterChart');
    if (clusterChart) {
        const ctx = clusterChart.getContext('2d');
        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Volatilite', 'Ortalama Değişim', 'Beta', 'Risk-Getiri Oranı'],
                datasets: window.clusterData || []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Sayfa yüklendiğinde smooth scroll efekti ekle
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Scroll olduğunda navbar'ı güncelle
    let lastScroll = 0;
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll <= 0) {
            navbar.classList.remove('scroll-up');
            return;
        }
        
        if (currentScroll > lastScroll && !navbar.classList.contains('scroll-down')) {
            // Aşağı scroll
            navbar.classList.remove('scroll-up');
            navbar.classList.add('scroll-down');
        } else if (currentScroll < lastScroll && navbar.classList.contains('scroll-down')) {
            // Yukarı scroll
            navbar.classList.remove('scroll-down');
            navbar.classList.add('scroll-up');
        }
        
        lastScroll = currentScroll;
    });

    // Sayfa yüklendiğinde URL parametrelerini uygula
    applyUrlParamsToForm();

    // Risk Profili Anketi doğrulama
    validateRiskProfileForm();
});

// Tablo sıralama fonksiyonu
function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[column];
    const isNumeric = header.classList.contains('numeric');
    const currentDirection = header.getAttribute('data-sort') || 'asc';
    const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
    
    // Sıralama yönünü güncelle
    table.querySelectorAll('th').forEach(th => {
        th.removeAttribute('data-sort');
        th.classList.remove('sort-asc', 'sort-desc');
    });
    header.setAttribute('data-sort', newDirection);
    header.classList.add(newDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    
    // Satırları sırala
    rows.sort((a, b) => {
        const aValue = a.cells[column].textContent.trim();
        const bValue = b.cells[column].textContent.trim();
        
        if (isNumeric) {
            return newDirection === 'asc' 
                ? parseFloat(aValue) - parseFloat(bValue)
                : parseFloat(bValue) - parseFloat(aValue);
        } else {
            return newDirection === 'asc'
                ? aValue.localeCompare(bValue, 'tr')
                : bValue.localeCompare(aValue, 'tr');
        }
    });
    
    // Sıralanmış satırları tabloya ekle
    rows.forEach(row => tbody.appendChild(row));
}

// Hisse detaylarını yükle
async function loadStockDetails(stockCode) {
    // Yükleme göstergesi
    const loadingElement = document.querySelector('.loading-indicator');
    const modalContent = document.querySelector('.modal-content');
    
    if (modalContent) {
        modalContent.innerHTML = `
            <span class="close-modal">&times;</span>
            <div class="loading-indicator">
                <div class="spinner"></div>
                <p>Veriler yükleniyor...</p>
            </div>
        `;
    }
    
    // Geçerli token kontrol et
    const tokenValid = await ensureValidToken();
    if (!tokenValid) {
        if (modalContent) {
            modalContent.innerHTML = `
                <span class="close-modal">&times;</span>
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>API erişim tokeni alınamadı. Lütfen giriş yapın veya daha sonra tekrar deneyin.</p>
                    <button class="retry-button" onclick="loadStockDetails('${stockCode}')">Tekrar Dene</button>
                </div>
            `;
        }
        return;
    }
    
    // Zaman aşımı süresi için controller tanımlama
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 saniye zaman aşımı
    
    // API'den hisse detaylarını al
    fetch(`/api/stocks/${stockCode}`, {
        signal: controller.signal,
        headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Authorization': `Bearer ${apiToken}`
        }
    })
        .then(response => {
            clearTimeout(timeoutId); // İstek tamamlandığında zaman aşımını temizle
            
            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('API erişim yetkisi yok. Lütfen giriş yapın.');
                } else if (response.status === 404) {
                    throw new Error(`"${stockCode}" kodlu hisse bulunamadı.`);
                } else {
                    throw new Error(`HTTP hata! durum: ${response.status}`);
                }
            }
            return response.json();
        })
        .then(data => {
            // Modal içeriğini güncelle
            if (modalContent) {
                modalContent.innerHTML = `
                    <span class="close-modal">&times;</span>
                    <h2>${data.code} - ${data.name}</h2>
                    <div class="stock-metrics">
                        <div class="metric">
                            <span class="label">Ortalama Fiyat</span>
                            <span class="value">${parseFloat(data.avg_price).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})} ₺</span>
                        </div>
                        <div class="metric">
                            <span class="label">Volatilite</span>
                            <span class="value">${parseFloat(data.volatility).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</span>
                        </div>
                        <div class="metric">
                            <span class="label">Ortalama Günlük Değişim</span>
                            <span class="value ${data.avg_change >= 0 ? 'positive' : 'negative'}">${parseFloat(data.avg_change).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}%</span>
                        </div>
                        <div class="metric">
                            <span class="label">Beta</span>
                            <span class="value">${parseFloat(data.beta).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                        </div>
                    </div>
                    <div class="stock-chart">
                        <canvas id="stockPriceChart"></canvas>
                    </div>
                `;
                
                try {
                    // Fiyat grafiğini çiz
                    const ctx = document.getElementById('stockPriceChart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.price_history.dates,
                            datasets: [{
                                label: 'Kapanış Fiyatı',
                                data: data.price_history.prices,
                                borderColor: '#4285F4',
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            locale: 'tr-TR',
                            scales: {
                                y: {
                                    ticks: {
                                        callback: function(value) {
                                            return value.toLocaleString('tr-TR') + ' ₺';
                                        }
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            let label = context.dataset.label || '';
                                            if (label) {
                                                label += ': ';
                                            }
                                            if (context.parsed.y !== null) {
                                                label += new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 2 }).format(context.parsed.y) + ' ₺';
                                            }
                                            return label;
                                        }
                                    }
                                }
                            }
                        }
                    });
                } catch (chartError) {
                    console.error('Grafik oluşturulurken hata:', chartError);
                    const chartContainer = document.querySelector('.stock-chart');
                    if (chartContainer) {
                        chartContainer.innerHTML = '<div class="error-message">Grafik yüklenemedi.</div>';
                    }
                }
            }
        })
        .catch(error => {
            clearTimeout(timeoutId); // Hata durumunda da zaman aşımını temizle
            console.error('Hisse detayları yüklenirken hata oluştu:', error);
            
            let errorMessage = 'Veri yüklenirken bir hata oluştu. Lütfen tekrar deneyin.';
            
            // Özel hata mesajları
            if (error.name === 'AbortError') {
                errorMessage = 'İstek zaman aşımına uğradı. Sunucu yanıt vermiyor.';
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            if (modalContent) {
                modalContent.innerHTML = `
                    <span class="close-modal">&times;</span>
                    <div class="error-message">
                        <i class="fas fa-exclamation-circle"></i>
                        <p>${errorMessage}</p>
                        <button class="retry-button" onclick="loadStockDetails('${stockCode}')">Tekrar Dene</button>
                    </div>
                `;
            }
        });
}

// Form filtreleme
const filterForm = document.querySelector('.filter-form');
if (filterForm) {
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const params = new URLSearchParams(formData);
        
        // Sayfayı filtreleme parametreleriyle yeniden yükle
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    });
}

// Sayfa yüklendiğinde URL parametrelerini forma uygula
function applyUrlParamsToForm() {
    const form = document.querySelector('.filter-form');
    if (form) {
        const params = new URLSearchParams(window.location.search);
        for (const [key, value] of params) {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }
    }
}

// Risk Profili Anketi doğrulama
function validateRiskProfileForm() {
    const riskForm = document.getElementById('risk-profile-form');
    
    if (riskForm) {
        riskForm.addEventListener('submit', function(e) {
            const questions = this.querySelectorAll('.risk-question');
            let valid = true;
            let firstInvalidQuestion = null;
            
            // Tüm soruları kontrol et
            questions.forEach(question => {
                const selectedOption = question.querySelector('input[type="radio"]:checked');
                const errorMessage = question.querySelector('.validation-error');
                
                // Seçim yapılmamışsa
                if (!selectedOption) {
                    valid = false;
                    
                    // İlk hatalı soruyu kaydet
                    if (!firstInvalidQuestion) {
                        firstInvalidQuestion = question;
                    }
                    
                    // Hata mesajı göster
                    if (errorMessage) {
                        errorMessage.style.display = 'block';
                    } else {
                        const error = document.createElement('div');
                        error.className = 'validation-error text-red-500 text-sm mt-1';
                        error.textContent = 'Lütfen bir seçenek seçin';
                        question.querySelector('.risk-options').appendChild(error);
                    }
                } else if (errorMessage) {
                    // Seçim yapılmışsa hata mesajını gizle
                    errorMessage.style.display = 'none';
                }
            });
            
            // Form geçerli değilse gönderimi engelle
            if (!valid) {
                e.preventDefault();
                
                // İlk hatalı soruya kaydır
                if (firstInvalidQuestion) {
                    firstInvalidQuestion.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
        
        // Bir seçenek seçildiğinde hata mesajını gizle
        riskForm.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('change', function() {
                const question = this.closest('.risk-question');
                const errorMessage = question.querySelector('.validation-error');
                if (errorMessage) {
                    errorMessage.style.display = 'none';
                }
            });
        });
    }
}

// API token yönetimi
let apiToken = localStorage.getItem('api_token');
let tokenExpiry = localStorage.getItem('token_expiry');

// API anahtarını güvenli şekilde almak için
async function getApiKey() {
    try {
        // İdeal olarak bu endpoint API anahtarını güvenli şekilde sunmalı
        // Gerçek bir uygulamada kullanıcı kimlik doğrulaması gerekir
        const response = await fetch('/api/auth/get-api-key', {
            method: 'GET',
            credentials: 'include', // Cookie'leri dahil et
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`API anahtarı alınamadı: ${response.status}`);
        }
        
        const data = await response.json();
        return data.api_key;
    } catch (error) {
        console.error('API anahtarı alınırken hata oluştu:', error);
        // Burada varsayılan bir değer kullanmak yerine hata fırlatıyoruz
        throw error;
    }
}

async function ensureValidToken() {
    // Token yoksa veya süresi dolmuşsa yeni token al
    const now = Math.floor(Date.now() / 1000);
    if (!apiToken || !tokenExpiry || parseInt(tokenExpiry) < now) {
        try {
            // API anahtarını güvenli bir şekilde al
            const apiKey = await getApiKey();
            
            const response = await fetch('/api/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    api_key: apiKey,
                    expires: now + 3600 // 1 saat geçerli
                })
            });
            
            if (!response.ok) {
                throw new Error(`Token alınamadı: ${response.status}`);
            }
            
            const data = await response.json();
            apiToken = data.token;
            tokenExpiry = data.expires;
            
            // Local storage'a kaydet
            localStorage.setItem('api_token', apiToken);
            localStorage.setItem('token_expiry', tokenExpiry);
        } catch (error) {
            console.error('API token alınırken hata:', error);
            return false;
        }
    }
    return true;
} 