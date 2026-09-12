/**
 * PriceRunner DTU / CartCompare — Search Controller & Results Renderer
 * 
 * Inspired by Lovable Canvas Aesthetic.
 * Handles search input, API calls, dynamic themes, store filtering, and card rendering.
 */

(function () {
    'use strict';

    // ── DOM References ──
    const searchInput = document.getElementById('search-input');
    const searchSubmitBtn = document.getElementById('search-submit-btn');
    const searchLoader = document.getElementById('search-loader');
    const searchKbd = document.querySelector('.search-box__kbd');
    const skeletonContainer = document.getElementById('skeleton-container');
    const resultsSection = document.getElementById('results-section');
    const matchedSection = document.getElementById('matched-section');
    const matchedGrid = document.getElementById('matched-grid');
    const matchedCount = document.getElementById('matched-count');
    const unmatchedSection = document.getElementById('unmatched-section');
    const unmatchedGrid = document.getElementById('unmatched-grid');
    const unmatchedCount = document.getElementById('unmatched-count');
    const statusBar = document.getElementById('status-bar');
    const statusHeading = document.getElementById('status-heading');
    const statusCountLead = document.getElementById('status-count-lead');
    const statusQuery = document.getElementById('status-query');
    const statusMeta = document.getElementById('status-meta');
    const statusPlatforms = document.getElementById('status-platforms');
    const strategySelect = document.getElementById('strategy-select');
    const storeFilter = document.getElementById('store-filter');
    const errorBanner = document.getElementById('error-banner');
    const errorText = document.getElementById('error-text');
    const errorClose = document.getElementById('error-close');
    const heroSection = document.getElementById('hero-section');
    const quickTags = document.getElementById('quick-tags');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeToggleIcon = document.getElementById('theme-toggle-icon');
    const themeToggleLabel = document.getElementById('theme-toggle-label');

    // Controls & Filters Bar elements
    const resultsControlsBar = document.getElementById('results-controls-bar');
    const sortPills = document.getElementById('sort-pills');
    const filterPills = document.getElementById('filter-pills');
    const brandFilterRow = document.getElementById('brand-filter-row');
    const brandPills = document.getElementById('brand-pills');
    const controlsShowingCount = document.getElementById('controls-showing-count');
    const btnResetFilters = document.getElementById('btn-reset-filters');

    // ── State ──
    let debounceTimer = null;
    let lastQuery = '';
    let lastResult = null;
    let currentStoreFilter = 'all';
    let currentMatchedPairs = [];
    let currentUnmatched = {};
    let activeFilter = 'all';
    let activeBrand = 'all';
    let activeSort = 'best_match';

    // ── Theme Management ──
    function initTheme() {
        const savedTheme = localStorage.getItem('pricerunner_theme') || 'light';
        setTheme(savedTheme);

        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
                const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
                setTheme(nextTheme);
            });
        }
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('pricerunner_theme', theme);
        if (themeToggleIcon) {
            themeToggleIcon.textContent = theme === 'light' ? '🌙' : '☀️';
        }
        if (themeToggleLabel) {
            themeToggleLabel.textContent = theme === 'light' ? 'Dark' : 'Light';
        }
    }

    // ── Initialize ──
    function init() {
        initTheme();

        // Logo / Home click: reset to clean homepage state
        const brandHome = document.getElementById('header-brand-home');
        if (brandHome) {
            brandHome.addEventListener('click', (e) => {
                e.preventDefault();
                resetToHome();
            });
        }

        // Search inputs
        if (searchInput) {
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const q = searchInput.value.trim();
                    if (q) performSearch(q);
                }
            });

            searchInput.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                const q = searchInput.value.trim();
                if (q.length >= 2) {
                    debounceTimer = setTimeout(() => performSearch(q), 450);
                }
            });
        }

        if (searchSubmitBtn) {
            searchSubmitBtn.addEventListener('click', () => {
                const q = searchInput.value.trim();
                if (q) performSearch(q);
            });
        }

        // Quick tag buttons
        if (quickTags) {
            quickTags.addEventListener('click', (e) => {
                const tag = e.target.closest('.tag');
                if (tag) {
                    const query = tag.dataset.query;
                    searchInput.value = query;
                    performSearch(query);
                }
            });
        }

        // Strategy selector
        if (strategySelect) {
            strategySelect.addEventListener('change', () => {
                if (lastQuery) performSearch(lastQuery);
            });
        }

        // Store filter segmented tabs (Both, Blinkit, Instamart)
        if (storeFilter) {
            storeFilter.addEventListener('click', (e) => {
                const tab = e.target.closest('.filter-tab');
                if (!tab) return;
                storeFilter.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentStoreFilter = tab.dataset.store || 'all';
                applySortAndFilter();
            });
        }

        // Sort pills click handler
        if (sortPills) {
            sortPills.addEventListener('click', (e) => {
                const pill = e.target.closest('.control-pill');
                if (!pill || !pill.dataset.sort) return;
                sortPills.querySelectorAll('.control-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                activeSort = pill.dataset.sort;
                applySortAndFilter();
            });
        }

        // Filter pills click handler
        if (filterPills) {
            filterPills.addEventListener('click', (e) => {
                const pill = e.target.closest('.control-pill');
                if (!pill || !pill.dataset.filter) return;
                filterPills.querySelectorAll('.control-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                activeFilter = pill.dataset.filter;
                applySortAndFilter();
            });
        }

        // Brand pills click handler (delegated)
        if (brandPills) {
            brandPills.addEventListener('click', (e) => {
                const pill = e.target.closest('.control-pill');
                if (!pill || !pill.dataset.brand) return;
                brandPills.querySelectorAll('.control-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                activeBrand = pill.dataset.brand;
                applySortAndFilter();
            });
        }

        // Reset filters button click
        if (btnResetFilters) {
            btnResetFilters.addEventListener('click', () => {
                resetFilters();
            });
        }

        // Error banner close
        if (errorClose) {
            errorClose.addEventListener('click', () => {
                errorBanner.style.display = 'none';
            });
        }

        // Collapsible footer toggle (collapsed by default)
        const footerToggleBtn = document.getElementById('footer-toggle-btn');
        const mainFooter = document.getElementById('main-footer');
        const footerDetails = document.getElementById('footer-details');
        const footerToggleText = document.getElementById('footer-toggle-text');

        if (footerToggleBtn && mainFooter && footerDetails) {
            footerToggleBtn.addEventListener('click', () => {
                const isExpanded = mainFooter.classList.toggle('footer--expanded');
                footerDetails.style.display = isExpanded ? 'flex' : 'none';
                footerToggleBtn.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
                if (footerToggleText) {
                    footerToggleText.textContent = isExpanded ? 'Hide' : 'Info & Disclaimer';
                }
            });
        }
    }

    // ── Reset Filters Helper ──
    function resetFilters() {
        activeFilter = 'all';
        activeBrand = 'all';
        activeSort = 'best_match';
        currentStoreFilter = 'all';

        if (storeFilter) {
            storeFilter.querySelectorAll('.filter-tab').forEach(t => {
                t.classList.toggle('active', t.dataset.store === 'all');
            });
        }
        if (sortPills) {
            sortPills.querySelectorAll('.control-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.sort === 'best_match');
            });
        }
        if (filterPills) {
            filterPills.querySelectorAll('.control-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.filter === 'all');
            });
        }
        if (brandPills) {
            brandPills.querySelectorAll('.control-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.brand === 'all');
            });
        }

        applySortAndFilter();
    }

    // ── Brand Chips Generator ──
    function renderBrandChips(pairs) {
        if (!brandFilterRow || !brandPills) return;

        const brandCounts = {};
        pairs.forEach(pair => {
            const brandsFound = new Set();
            Object.values(pair.products || {}).forEach(prod => {
                if (prod && prod.brand) {
                    const b = prod.brand.trim();
                    if (b.length > 1 && b.toLowerCase() !== 'grocery' && b.toLowerCase() !== 'generic') {
                        const formatted = b.charAt(0).toUpperCase() + b.slice(1);
                        brandsFound.add(formatted);
                    }
                }
            });
            brandsFound.forEach(b => {
                brandCounts[b] = (brandCounts[b] || 0) + 1;
            });
        });

        const sortedBrands = Object.entries(brandCounts)
            .filter(([_, count]) => count >= 1)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        if (sortedBrands.length >= 2) {
            brandFilterRow.style.display = 'flex';
            let pillsHtml = `
                <button type="button" class="control-pill ${activeBrand === 'all' ? 'active' : ''}" data-brand="all">
                    All Brands
                </button>
            `;
            sortedBrands.forEach(([brand, count]) => {
                const isActive = activeBrand.toLowerCase() === brand.toLowerCase();
                pillsHtml += `
                    <button type="button" class="control-pill ${isActive ? 'active' : ''}" data-brand="${escapeHtml(brand)}">
                        ${escapeHtml(brand)} <span style="opacity:0.65;font-size:0.7em">(${count})</span>
                    </button>
                `;
            });
            brandPills.innerHTML = pillsHtml;
        } else {
            brandFilterRow.style.display = 'none';
            activeBrand = 'all';
        }
    }

    // ── Metric Helpers for Sorting ──
    function getMinPrice(pair) {
        let min = Infinity;
        Object.values(pair.products || {}).forEach(p => {
            if (p && typeof p.price === 'number' && p.price < min) {
                min = p.price;
            }
        });
        return min === Infinity ? 999999 : min;
    }

    function getMinUnitPrice(pair) {
        let min = Infinity;
        Object.values(pair.products || {}).forEach(p => {
            if (p) {
                if (p.weight && typeof p.weight.unit_price === 'number' && p.weight.unit_price > 0) {
                    if (p.weight.unit_price < min) min = p.weight.unit_price;
                } else if (p.unit_price_label) {
                    const match = p.unit_price_label.match(/₹([\d.]+)/);
                    if (match) {
                        const val = parseFloat(match[1]);
                        if (val < min) min = val;
                    }
                }
            }
        });
        return min === Infinity ? getMinPrice(pair) : min;
    }

    function getMaxRating(pair) {
        let max = -1;
        Object.values(pair.products || {}).forEach(p => {
            if (p && p.rating && p.rating > max) {
                max = parseFloat(p.rating);
            }
        });
        return max;
    }

    // ── Apply Sort and Filter Controller ──
    function applySortAndFilter() {
        if (!currentMatchedPairs || currentMatchedPairs.length === 0) {
            if (resultsControlsBar) resultsControlsBar.style.display = 'none';
            matchedGrid.innerHTML = '';
            return;
        }

        if (resultsControlsBar) resultsControlsBar.style.display = 'block';

        // 1. Filter
        let filtered = currentMatchedPairs.filter(pair => {
            const platforms = Object.keys(pair.products || {});

            // Store Filter tab
            if (currentStoreFilter === 'blinkit' && !platforms.includes('blinkit')) return false;
            if (currentStoreFilter === 'instamart' && !platforms.includes('instamart')) return false;

            // Brand Filter
            if (activeBrand !== 'all') {
                const bLower = activeBrand.toLowerCase();
                const matchesBrand = Object.values(pair.products || {}).some(p => 
                    (p.brand && p.brand.toLowerCase() === bLower) ||
                    (p.raw_name && p.raw_name.toLowerCase().includes(bLower))
                );
                if (!matchesBrand && !pair.canonical_name.toLowerCase().includes(bLower)) {
                    return false;
                }
            }

            // Deal & Quality Filters
            switch (activeFilter) {
                case 'in_stock':
                    return Object.values(pair.products || {}).some(p => p.in_stock);
                case 'cheaper_blinkit':
                    return pair.cheaper_platform === 'blinkit' && (pair.price_diff || 0) > 0;
                case 'cheaper_instamart':
                    return pair.cheaper_platform === 'instamart' && (pair.price_diff || 0) > 0;
                case 'same_price':
                    return (pair.price_diff === 0 || Math.abs(pair.price_diff || 0) < 0.01) && platforms.length > 1;
                case 'high_confidence':
                    return (pair.confidence || 0) >= 0.8;
                case 'rated_only':
                    return Object.values(pair.products || {}).some(p => p.rating && p.rating > 0);
                case 'all':
                default:
                    return true;
            }
        });

        // 2. Sort
        const sorted = [...filtered].sort((a, b) => {
            switch (activeSort) {
                case 'price_asc':
                    return getMinPrice(a) - getMinPrice(b);
                case 'price_desc':
                    return getMinPrice(b) - getMinPrice(a);
                case 'unit_price_asc':
                    return getMinUnitPrice(a) - getMinUnitPrice(b);
                case 'savings_desc':
                    return (b.price_diff || 0) - (a.price_diff || 0);
                case 'rating_desc':
                    return getMaxRating(b) - getMaxRating(a);
                case 'best_match':
                default:
                    return (b.confidence || 0) - (a.confidence || 0);
            }
        });

        // 3. Render Cards
        matchedGrid.innerHTML = '';
        if (sorted.length > 0) {
            sorted.forEach((pair, idx) => {
                matchedGrid.appendChild(createComparisonCard(pair, idx));
            });
            matchedSection.style.display = 'block';
        } else {
            // Empty state for filters
            matchedSection.style.display = 'block';
            matchedGrid.innerHTML = `
                <div class="controls-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--bg-card); border: 1px dashed var(--border); border-radius: var(--radius-lg);">
                    <div style="font-size: 2.5rem; margin-bottom: 12px;">🔍</div>
                    <h4 style="font-family: var(--font-display); font-size: 1.125rem; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">No products match these filters</h4>
                    <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 16px;">Try clearing your filters or choosing a different sorting option.</p>
                    <button type="button" class="btn btn--primary" id="btn-empty-reset" style="margin: 0 auto; display: inline-flex; cursor: pointer;">Reset All Filters</button>
                </div>
            `;
            const btnEmptyReset = document.getElementById('btn-empty-reset');
            if (btnEmptyReset) {
                btnEmptyReset.addEventListener('click', resetFilters);
            }
        }

        // 4. Update Summary & Reset Button
        if (matchedCount) {
            matchedCount.textContent = `(${sorted.length})`;
        }

        const isFiltered = (activeFilter !== 'all') || (activeBrand !== 'all') || (activeSort !== 'best_match') || (currentStoreFilter !== 'all');
        if (controlsShowingCount) {
            if (isFiltered) {
                controlsShowingCount.textContent = `Showing ${sorted.length} of ${currentMatchedPairs.length} matched deals`;
            } else {
                controlsShowingCount.textContent = `Showing all ${currentMatchedPairs.length} matched deals`;
            }
        }

        if (btnResetFilters) {
            btnResetFilters.style.display = isFiltered ? 'inline-flex' : 'none';
        }
    }

    // ── Search Execution ──
    async function performSearch(query) {
        if (query === lastQuery && lastResult) {
            const strat = strategySelect ? strategySelect.value : 'hybrid';
            if (lastResult._strategy === strat) return;
        }

        lastQuery = query;
        showLoading();
        hideError();

        const strategy = strategySelect ? strategySelect.value : 'hybrid';

        try {
            const url = `/api/search?q=${encodeURIComponent(query)}&strategy=${strategy}&debug=true`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            data._strategy = strategy;
            lastResult = data;

            hideLoading();
            renderResults(data);
        } catch (error) {
            hideLoading();
            showError(error.message || 'Failed to fetch comparison results. Please try again.');
            console.error('Search error:', error);
        }
    }

    // ── Render Results ──
    function renderResults(data) {
        // Collapse hero section
        if (heroSection) {
            heroSection.classList.add('hero--collapsed');
        }

        // Update status bar
        if (statusBar) statusBar.style.display = 'block';

        currentMatchedPairs = data.matched_pairs || [];
        currentUnmatched = data.unmatched || {};
        const count = currentMatchedPairs.length;

        if (statusHeading && statusCountLead) {
            statusCountLead.textContent = `${count} ${count === 1 ? 'match' : 'matches'} for`;
        }
        if (statusQuery) {
            statusQuery.textContent = `“${data.query}”`;
        }

        const meta = data.metadata || {};
        const timeStr = meta.total_time ? `${meta.total_time.toFixed(2)}s` : '';
        const cacheStr = meta.cache_hit ? '· Cached' : '· Live scrape';
        if (statusMeta) {
            statusMeta.textContent = `Matched across both stores · Updated just now ${timeStr ? `(${timeStr} ${cacheStr})` : ''}`.trim();
        }

        // Platform badges
        if (statusPlatforms) {
            statusPlatforms.innerHTML = '';
            const allPlatforms = [...(meta.platforms_available || []), ...(meta.platforms_failed || [])];
            allPlatforms.forEach(p => {
                const isDown = (meta.platforms_failed || []).includes(p);
                const badge = document.createElement('span');
                badge.className = `platform-badge platform-badge--${p} ${isDown ? 'platform-badge--down' : ''}`;
                badge.textContent = isDown ? `${formatPlatformName(p)} ✕` : `${formatPlatformName(p)} ✓`;
                statusPlatforms.appendChild(badge);
            });
        }

        if (meta.platforms_failed && meta.platforms_failed.length > 0) {
            const failedNames = meta.platforms_failed.map(formatPlatformName).join(', ');
            showError(`${failedNames} unavailable. Showing results from available platforms only.`);
        }

        // Reset filter states for new search
        activeFilter = 'all';
        activeBrand = 'all';
        activeSort = 'best_match';
        currentStoreFilter = 'all';

        if (storeFilter) {
            storeFilter.querySelectorAll('.filter-tab').forEach(t => {
                t.classList.toggle('active', t.dataset.store === 'all');
            });
        }
        if (sortPills) {
            sortPills.querySelectorAll('.control-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.sort === 'best_match');
            });
        }
        if (filterPills) {
            filterPills.querySelectorAll('.control-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.filter === 'all');
            });
        }

        // Build dynamic brand pills
        renderBrandChips(currentMatchedPairs);

        // Apply sort & filters to matched items
        applySortAndFilter();

        // Render unmatched
        unmatchedGrid.innerHTML = '';
        let totalUnmatched = 0;

        Object.entries(currentUnmatched).forEach(([platform, products]) => {
            products.forEach(product => {
                totalUnmatched++;
                unmatchedGrid.appendChild(createSingleCard(product, platform));
            });
        });

        if (totalUnmatched > 0) {
            unmatchedSection.style.display = 'block';
            if (unmatchedCount) unmatchedCount.textContent = `(${totalUnmatched})`;
        } else {
            unmatchedSection.style.display = 'none';
        }

        resultsSection.style.display = 'block';
        resultsSection.style.animation = 'fade-in 0.35s ease';
    }

    // ── Create Comparison Card (Lovable Aesthetic with Rich Details) ──
    function createComparisonCard(pair, index) {
        const card = document.createElement('div');
        card.className = 'compare-card';
        card.style.animationDelay = `${index * 0.04}s`;
        card.style.animation = 'slide-in 0.35s ease both';

        const platforms = Object.keys(pair.products || {});
        const hasBlinkit = platforms.includes('blinkit');
        const hasInstamart = platforms.includes('instamart');

        card.dataset.hasBlinkit = hasBlinkit ? 'true' : 'false';
        card.dataset.hasInstamart = hasInstamart ? 'true' : 'false';

        const productA = pair.products['blinkit'] || pair.products[platforms[0]];
        const productB = pair.products['instamart'] || pair.products[platforms[1]];

        const confidenceClass = pair.confidence >= 0.8 ? 'high' :
            pair.confidence >= 0.5 ? 'medium' : 'low';

        // Extract category or tag from variant / brand
        const primaryProduct = productA || productB || {};
        const brandName = primaryProduct.brand ? primaryProduct.brand.toUpperCase() : 'GROCERY';
        const weightText = primaryProduct.raw_weight_text || (primaryProduct.weight && primaryProduct.weight.raw_text) || '';
        const packText = (primaryProduct.weight && primaryProduct.weight.pack_count > 1) ? `Pack of ${primaryProduct.weight.pack_count}` : '';
        const metaLine = [weightText, packText].filter(Boolean).join(' · ');

        // Savings & Best Price calculation
        let savingsHtml = '';
        let bestPriceTag = '';
        const minPrice = Math.min(...platforms.map(p => pair.products[p] ? pair.products[p].price : 999999));

        if (minPrice && minPrice < 999999) {
            bestPriceTag = `<span class="badge-tag badge-tag--savings">Best from ₹${minPrice.toFixed(0)}</span>`;
        }

        if (pair.price_diff > 0 && pair.cheaper_platform) {
            const pctStr = pair.price_diff_pct > 0 ? ` (${pair.price_diff_pct}%)` : '';
            savingsHtml = `
                <div class="compare-card__savings-tag">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m5 12 5 5L20 7"/></svg>
                    Save ₹${pair.price_diff.toFixed(0)} on ${formatPlatformName(pair.cheaper_platform)}${pctStr}
                </div>`;
        } else if (pair.price_diff === 0 && platforms.length > 1) {
            savingsHtml = `
                <div class="compare-card__savings-tag" style="color:var(--text-muted)">
                    Same price on both stores
                </div>`;
        }

        // Product Avatar or Image
        const initialLetter = pair.canonical_name ? pair.canonical_name.trim().charAt(0).toUpperCase() : 'P';
        const imageUrl = (productA && productA.image_url) || (productB && productB.image_url) || '';
        const avatarHtml = imageUrl ?
            `<div class="compare-card__avatar"><img src="${imageUrl}" alt="${escapeHtml(pair.canonical_name)}" onerror="this.parentElement.innerHTML='${initialLetter}'"></div>` :
            `<div class="compare-card__avatar">${initialLetter}</div>`;

        // Store Rows
        let storeRowsHtml = '';
        const orderedPlatforms = ['blinkit', 'instamart'].filter(p => platforms.includes(p));
        platforms.forEach(p => {
            if (!orderedPlatforms.includes(p)) orderedPlatforms.push(p);
        });

        orderedPlatforms.forEach(pid => {
            const prod = pair.products[pid];
            if (!prod) return;

            const isCheaper = pid === pair.cheaper_platform;
            const deliveryTime = pid === 'blinkit' ? '8-10 min' : '10-15 min';
            const storeInitial = pid === 'blinkit' ? 'B' : 'I';

            const mrpHtml = (prod.mrp && prod.mrp > prod.price) ?
                `<span class="store-row__mrp">₹${prod.mrp.toFixed(0)}</span>` : '';
            const unitHtml = prod.unit_price_label ?
                `<div class="store-row__unit">${prod.unit_price_label}</div>` : '';

            const stockText = prod.in_stock ? 'In stock' : 'Out of stock';
            const stockClass = prod.in_stock ? 'stock--in' : 'stock--out';

            // ── Pack Weight / Size Badge ──
            let weightBadgeHtml = '';
            let pWeightText = prod.raw_weight_text || (prod.weight && prod.weight.raw_text) || '';
            if (!pWeightText && prod.unit_amount && prod.unit) {
                pWeightText = `${prod.unit_amount} ${prod.unit}`;
            }
            const pPackText = prod.weight && prod.weight.pack_count > 1 ? `Pack of ${prod.weight.pack_count}` : '';
            const pWeightFull = [pWeightText, pPackText].filter(Boolean).join(' · ');
            if (pWeightFull) {
                weightBadgeHtml = `<span class="store-row__weight-tag" title="Pack Size">📦 ${escapeHtml(pWeightFull)}</span>`;
            }

            // ── Platform Rating Badge ──
            let ratingBadgeHtml = '';
            if (prod.rating && prod.rating > 0) {
                const rNum = typeof prod.rating === 'number' ? prod.rating.toFixed(1) : parseFloat(prod.rating).toFixed(1);
                const rCount = prod.rating_count ? `<span class="store-row__rating-count">(${escapeHtml(String(prod.rating_count))})</span>` : '';
                ratingBadgeHtml = `<span class="store-row__rating" title="Rating on ${formatPlatformName(pid)}"><span class="store-row__rating-star">⭐</span> ${rNum} ${rCount}</span>`;
            }

            // ── Discount Tag (if MRP > Price) ──
            let discountBadgeHtml = '';
            if (prod.mrp && prod.price && prod.mrp > prod.price) {
                const discPct = Math.round(((prod.mrp - prod.price) / prod.mrp) * 100);
                if (discPct >= 3) {
                    discountBadgeHtml = `<span class="store-row__discount-tag">${discPct}% OFF</span>`;
                }
            }

            const metaBadgesHtml = (weightBadgeHtml || ratingBadgeHtml || discountBadgeHtml) ? `
                <div class="store-row__meta-badges">
                    ${weightBadgeHtml}
                    ${ratingBadgeHtml}
                    ${discountBadgeHtml}
                </div>
            ` : '';

            storeRowsHtml += `
                <div class="store-row ${isCheaper ? 'store-row--winner' : ''}">
                    <div class="store-row__badge store-row__badge--${pid}">${storeInitial}</div>
                    <div class="store-row__info">
                        <div class="store-row__name-line">
                            <span class="store-row__name">${formatPlatformName(pid)}</span>
                            ${isCheaper ? '<span class="badge-tag badge-tag--savings" style="font-size:0.625rem; padding:1px 5px;">Cheapest</span>' : ''}
                        </div>
                        <div class="store-row__delivery">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                            <span>${deliveryTime}</span> · <span class="store-row__stock ${stockClass}">${stockText}</span>
                        </div>
                        ${metaBadgesHtml}
                    </div>
                    <div class="store-row__pricing">
                        <div class="store-row__price">₹${prod.price.toFixed(0)} ${mrpHtml}</div>
                        ${unitHtml}
                    </div>
                    ${prod.product_url ? `
                        <a href="${prod.product_url}" target="_blank" rel="noopener noreferrer" class="store-row__action" title="Open on ${formatPlatformName(pid)}">
                            <span>Open</span>
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M7 7h10v10"/><path d="M7 17 17 7"/></svg>
                        </a>
                    ` : ''}
                </div>
            `;
        });

        card.innerHTML = `
            <div class="compare-card__header">
                ${avatarHtml}
                <div class="compare-card__meta-wrap">
                    <div class="compare-card__badges">
                        <span class="badge-tag">${escapeHtml(brandName)}</span>
                        ${bestPriceTag}
                    </div>
                    <h3 class="compare-card__name">${escapeHtml(pair.canonical_name)}</h3>
                    ${metaLine ? `<div class="compare-card__pack-info">${escapeHtml(metaLine)}</div>` : ''}
                </div>
                <span class="compare-card__confidence confidence--${confidenceClass}">
                    ${(pair.confidence * 100).toFixed(0)}% match
                </span>
            </div>

            <div class="compare-card__stores">
                ${storeRowsHtml}
            </div>

            <div class="compare-card__footer">
                ${savingsHtml}
                <div class="compare-card__actions">
                    <button class="btn btn--cart add-to-cart-btn" 
                            data-pair='${JSON.stringify(pair).replace(/'/g, "&#39;")}'>
                        🛒 Add to Cart
                    </button>
                </div>
            </div>
        `;

        // Add to cart click handler
        const addBtn = card.querySelector('.add-to-cart-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                const pairData = JSON.parse(addBtn.dataset.pair);
                if (window.CartManager) {
                    window.CartManager.addItem(pairData);
                }
            });
        }

        return card;
    }

    // ── Create Single Card (Unmatched / Exclusive Items) ──
    function createSingleCard(product, platform) {
        const card = document.createElement('div');
        card.className = 'single-card';

        let unitHtml = product.unit_price_label ? `<span> · ${product.unit_price_label}</span>` : '';
        let stockHtml = product.in_stock ? '' : '<span class="price-col__stock stock--out" style="margin-left:8px">Out of Stock</span>';

        // Pack weight and rating tags for single cards
        let singleWeightText = product.raw_weight_text || (product.weight && product.weight.raw_text) || '';
        let singleWeightHtml = singleWeightText ? `<span class="store-row__weight-tag" style="margin-right:6px">📦 ${escapeHtml(singleWeightText)}</span>` : '';
        let singleRatingHtml = '';
        if (product.rating && product.rating > 0) {
            const rNum = typeof product.rating === 'number' ? product.rating.toFixed(1) : parseFloat(product.rating).toFixed(1);
            const rCount = product.rating_count ? ` (${escapeHtml(String(product.rating_count))})` : '';
            singleRatingHtml = `<span class="store-row__rating" style="margin-right:6px">⭐ ${rNum}${rCount}</span>`;
        }

        const imageHtml = product.image_url ? `
            <div style="text-align: center; margin-bottom: 12px; background: var(--bg-secondary); padding: 12px; border-radius: var(--radius-md);">
                <img src="${product.image_url}" alt="${escapeHtml(product.raw_name)}" style="max-height: 100px; max-width: 100%; object-fit: contain;" onerror="this.style.display='none'">
            </div>
        ` : '';

        card.innerHTML = `
            <div class="single-card__platform" style="color:var(--${platform})">${formatPlatformName(platform)} Exclusive</div>
            ${imageHtml}
            <div class="single-card__name">${escapeHtml(product.raw_name)}</div>
            <div class="single-card__price">₹${product.price.toFixed(0)}${stockHtml}</div>
            <div class="single-card__meta" style="display:flex; align-items:center; flex-wrap:wrap; gap:4px;">
                ${singleWeightHtml}
                ${singleRatingHtml}
                ${product.mrp && product.mrp > product.price ? `<span>MRP ₹${product.mrp.toFixed(0)}</span>` : ''}
                ${unitHtml}
            </div>
            ${product.product_url ? `
                <a href="${product.product_url}" target="_blank" rel="noopener noreferrer" class="store-row__action" style="margin-top:auto; align-self:flex-start;">
                    <span>View on ${formatPlatformName(platform)}</span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M7 7h10v10"/><path d="M7 17 17 7"/></svg>
                </a>
            ` : ''}
        `;

        return card;
    }

    // ── UI Helpers ──
    function showLoading() {
        if (skeletonContainer) skeletonContainer.style.display = 'block';
        if (resultsSection) resultsSection.style.display = 'none';
        if (searchLoader) searchLoader.style.display = 'flex';
        if (searchKbd) searchKbd.style.display = 'none';
    }

    function hideLoading() {
        if (skeletonContainer) skeletonContainer.style.display = 'none';
        if (searchLoader) searchLoader.style.display = 'none';
        if (searchKbd) searchKbd.style.display = 'inline';
    }

    function showError(message) {
        if (errorText) errorText.textContent = message;
        if (errorBanner) errorBanner.style.display = 'block';
    }

    function hideError() {
        if (errorBanner) errorBanner.style.display = 'none';
    }

    function formatPlatformName(id) {
        const names = { blinkit: 'Blinkit', instamart: 'Instamart' };
        return names[id] || id;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function resetToHome() {
        lastQuery = '';
        lastResult = null;
        if (searchInput) searchInput.value = '';
        if (heroSection) heroSection.classList.remove('hero--collapsed');
        if (statusBar) statusBar.style.display = 'none';
        if (resultsSection) resultsSection.style.display = 'none';
        if (resultsControlsBar) resultsControlsBar.style.display = 'none';
        if (errorBanner) errorBanner.style.display = 'none';
        if (skeletonContainer) skeletonContainer.style.display = 'none';
        if (matchedGrid) matchedGrid.innerHTML = '';
        if (unmatchedGrid) unmatchedGrid.innerHTML = '';
        activeFilter = 'all';
        activeBrand = 'all';
        activeSort = 'best_match';
        currentStoreFilter = 'all';
        currentMatchedPairs = [];
        currentUnmatched = {};
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (searchInput) searchInput.focus();
    }

    // ── Expose for External Callers / Cart ──
    window.PriceRunner = {
        getLastResult: () => lastResult,
        performSearch,
        setTheme,
        resetToHome
    };

    // ── Start ──
    init();
})();
