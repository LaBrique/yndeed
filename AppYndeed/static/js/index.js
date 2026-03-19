/**
 * Yndeed - Frontend utilisant l'API REST
 * Les données sont récupérées via /api/jobs/ et /api/stats/
 */

console.log("🚀 Yndeed API Client initialisé");

// ==================== Configuration ====================
const API_BASE_URL = '/api';

// ==================== État de l'application ====================
let currentPage = 1;
let currentKeywords = '';
let currentLocation = '';
let locationDebounceTimer = null;

// ==================== Éléments DOM ====================
const searchForm = document.getElementById('search-form');
const keywordsInput = document.getElementById('keywords');
const locationInput = document.getElementById('location');
const locationDropdown = document.getElementById('location-dropdown');
const searchBtn = document.getElementById('search-btn');
const searchText = document.getElementById('search-text');
const searchSpinner = document.getElementById('search-spinner');
const jobsTableBody = document.getElementById('jobs-table-body');
const paginationDiv = document.getElementById('pagination');
const statsLoading = document.getElementById('stats-loading');
const statsContent = document.getElementById('stats-content');

// ==================== Fonctions API ====================

/**
 * Récupère les suggestions de villes depuis l'API
 */
async function fetchLocations(query = '') {
    const url = `${API_BASE_URL}/locations/?q=${encodeURIComponent(query)}`;
    console.log(`📡 Appel API: GET ${url}`);
    
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    });
    
    if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`✅ Locations:`, data);
    return data.locations;
}

/**
 * Récupère les offres d'emploi depuis l'API
 */
async function fetchJobs(keywords = '', location = '', page = 1) {
    const params = new URLSearchParams();
    if (keywords) params.append('keywords', keywords);
    if (location) params.append('location', location);
    params.append('page', page);
    
    const url = `${API_BASE_URL}/jobs/?${params.toString()}`;
    console.log(`📡 Appel API: GET ${url}`);
    
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    });
    
    if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`✅ API Response:`, data);
    return data;
}

/**
 * Récupère les statistiques depuis l'API
 */
async function fetchStats() {
    const url = `${API_BASE_URL}/stats/`;
    console.log(`📡 Appel API: GET ${url}`);
    
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    });
    
    if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`✅ Stats:`, data);
    return data;
}

// ==================== Fonctions de rendu ====================

/**
 * Affiche les offres dans le tableau
 */
function renderJobs(jobs) {
    if (!jobsTableBody) return;
    
    if (jobs.length === 0) {
        jobsTableBody.innerHTML = `
            <tr>
                <td colspan="4" class="py-8 text-center text-gray-500">
                    Aucune offre trouvée. Essayez d'autres critères de recherche.
                </td>
            </tr>
        `;
        return;
    }
    
    jobsTableBody.innerHTML = jobs.map(job => `
        <tr class="border-t hover:bg-gray-50 transition-colors">
            <td class="py-3 px-4">${escapeHtml(job.title)}</td>
            <td class="py-3 px-4">${escapeHtml(job.company || 'Inconnu')}</td>
            <td class="py-3 px-4">${escapeHtml(job.location || 'Non précisé')}</td>
            <td class="py-3 px-4">
                ${job.job_url 
                    ? `<a href="${escapeHtml(job.job_url)}" target="_blank" class="text-blue-600 hover:underline">Voir l'offre ↗</a>`
                    : 'N/A'
                }
            </td>
        </tr>
    `).join('');
}

/**
 * Affiche la pagination
 */
function renderPagination(data) {
    if (!paginationDiv) return;
    
    const totalPages = Math.ceil(data.count / 10);
    
    if (totalPages <= 1) {
        paginationDiv.innerHTML = `<span class="text-gray-500">Page 1 / 1</span>`;
        return;
    }
    
    let html = '';
    
    // Bouton Précédent
    if (data.previous) {
        html += `
            <button onclick="goToPage(${currentPage - 1})" 
                    class="px-3 py-2 border rounded-lg hover:bg-blue-100 transition-colors">
                ← Précédent
            </button>
        `;
    }
    
    // Numéro de page
    html += `<span>Page ${currentPage} / ${totalPages}</span>`;
    
    // Bouton Suivant
    if (data.next) {
        html += `
            <button onclick="goToPage(${currentPage + 1})" 
                    class="px-3 py-2 border rounded-lg hover:bg-blue-100 transition-colors">
                Suivant →
            </button>
        `;
    }
    
    paginationDiv.innerHTML = html;
}

/**
 * Affiche les statistiques
 */
function renderStats(stats) {
    if (!statsContent || !statsLoading) return;
    
    statsLoading.classList.add('hidden');
    statsContent.classList.remove('hidden');
    statsContent.innerHTML = `
        📊 <strong>${stats.total_jobs}</strong> offres | 
        👥 <strong>${stats.total_users}</strong> utilisateurs | 
        🏢 <strong>${stats.total_companies}</strong> entreprises
    `;
}

// ==================== Fonctions utilitaires ====================

/**
 * Échappe les caractères HTML pour éviter les XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Affiche/masque le spinner de chargement
 */
function setLoading(isLoading) {
    if (searchText) searchText.textContent = isLoading ? 'Chargement...' : 'Rechercher';
    if (searchSpinner) searchSpinner.classList.toggle('hidden', !isLoading);
    if (searchBtn) searchBtn.disabled = isLoading;
}

// ==================== Actions ====================

/**
 * Effectue une recherche
 */
async function doSearch(page = 1) {
    currentKeywords = keywordsInput?.value || '';
    currentLocation = locationInput?.value || '';
    currentPage = page;
    
    setLoading(true);
    
    try {
        const data = await fetchJobs(currentKeywords, currentLocation, page);
        renderJobs(data.results);
        renderPagination(data);
        
        // Met à jour l'URL sans recharger la page
        const params = new URLSearchParams();
        if (currentKeywords) params.append('keywords', currentKeywords);
        if (currentLocation) params.append('location', currentLocation);
        if (page > 1) params.append('page', page);
        
        const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
        window.history.pushState({}, '', newUrl);
        
    } catch (error) {
        console.error('❌ Erreur lors de la recherche:', error);
        if (jobsTableBody) {
            jobsTableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="py-8 text-center text-red-500">
                        Erreur lors du chargement des offres. Veuillez réessayer.
                    </td>
                </tr>
            `;
        }
    } finally {
        setLoading(false);
    }
}

/**
 * Navigue vers une page spécifique
 */
function goToPage(page) {
    doSearch(page);
}

/**
 * Charge les statistiques
 */
async function loadStats() {
    try {
        const stats = await fetchStats();
        renderStats(stats);
    } catch (error) {
        console.error('❌ Erreur lors du chargement des stats:', error);
        if (statsLoading) statsLoading.textContent = 'Erreur de chargement des stats';
    }
}

// ==================== Autocomplete Villes ====================

/**
 * Affiche les suggestions de villes dans le dropdown
 */
function renderLocationSuggestions(locations) {
    if (!locationDropdown) return;
    
    if (locations.length === 0) {
        locationDropdown.classList.add('hidden');
        return;
    }
    
    locationDropdown.innerHTML = locations.map(city => `
        <div class="location-option px-4 py-2 hover:bg-blue-100 cursor-pointer transition-colors"
             data-city="${escapeHtml(city)}">
            📍 ${escapeHtml(city)}
        </div>
    `).join('');
    
    locationDropdown.classList.remove('hidden');
    
    // Ajouter les event listeners sur chaque option
    locationDropdown.querySelectorAll('.location-option').forEach(option => {
        option.addEventListener('click', () => {
            selectLocation(option.dataset.city);
        });
    });
}

/**
 * Sélectionne une ville depuis les suggestions
 */
function selectLocation(city) {
    if (locationInput) {
        locationInput.value = city;
    }
    if (locationDropdown) {
        locationDropdown.classList.add('hidden');
    }
    console.log(`📍 Ville sélectionnée: ${city}`);
}

/**
 * Gère la saisie dans le champ de localisation
 */
async function handleLocationInput() {
    const query = locationInput?.value?.trim() || '';
    
    // Ne pas chercher si moins de 2 caractères
    if (query.length < 2) {
        if (locationDropdown) locationDropdown.classList.add('hidden');
        return;
    }
    
    try {
        const locations = await fetchLocations(query);
        renderLocationSuggestions(locations);
    } catch (error) {
        console.error('❌ Erreur autocomplete:', error);
    }
}

/**
 * Ferme le dropdown si on clique ailleurs
 */
function handleClickOutside(event) {
    if (locationDropdown && locationInput) {
        if (!locationInput.contains(event.target) && !locationDropdown.contains(event.target)) {
            locationDropdown.classList.add('hidden');
        }
    }
}

// ==================== Event Listeners ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM chargé, initialisation...');
    
    // Récupère les paramètres de l'URL
    const urlParams = new URLSearchParams(window.location.search);
    if (keywordsInput) keywordsInput.value = urlParams.get('keywords') || '';
    if (locationInput) locationInput.value = urlParams.get('location') || '';
    currentPage = parseInt(urlParams.get('page')) || 1;
    
    // Charge les statistiques via l'API
    loadStats();
    
    // Gestion du formulaire de recherche
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault(); // Empêche le rechargement de page
            if (locationDropdown) locationDropdown.classList.add('hidden');
            doSearch(1);
        });
    }
    
    // Autocomplete pour les villes
    if (locationInput) {
        locationInput.addEventListener('input', () => {
            // Debounce : attend 300ms après la dernière frappe
            clearTimeout(locationDebounceTimer);
            locationDebounceTimer = setTimeout(handleLocationInput, 300);
        });
        
        // Afficher le dropdown quand on focus le champ
        locationInput.addEventListener('focus', () => {
            if (locationInput.value.length >= 2) {
                handleLocationInput();
            }
        });
    }
    
    // Fermer le dropdown si on clique ailleurs
    document.addEventListener('click', handleClickOutside);
    
    console.log('✅ Yndeed API Client prêt !');
});

// Expose goToPage pour les boutons de pagination
window.goToPage = goToPage;