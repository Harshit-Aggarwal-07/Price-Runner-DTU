/**
 * PriceRunner DTU — Cart Manager
 * 
 * Manages cart state (localStorage), renders cart sidebar,
 * and calls the optimization API.
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'pricerunner_cart';

    // ── DOM References ──
    const cartToggleBtn = document.getElementById('cart-toggle-btn');
    const cartCountBadge = document.getElementById('cart-count');
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-overlay');
    const cartCloseBtn = document.getElementById('cart-close-btn');
    const cartBody = document.getElementById('cart-body');
    const cartEmpty = document.getElementById('cart-empty');
    const cartItemsContainer = document.getElementById('cart-items');
    const cartFooter = document.getElementById('cart-footer');
    const optimizeBtn = document.getElementById('optimize-btn');
    const cartResult = document.getElementById('cart-result');

    // ── State ──
    let cartItems = loadCart();

    // ── Initialize ──
    function init() {
        cartToggleBtn.addEventListener('click', toggleCart);
        cartOverlay.addEventListener('click', closeCart);
        cartCloseBtn.addEventListener('click', closeCart);
        optimizeBtn.addEventListener('click', optimizeCart);
        updateCartUI();
    }

    function toggleCart() {
        const isOpen = cartSidebar.classList.contains('open');
        if (isOpen) closeCart();
        else openCart();
    }

    function openCart() {
        cartSidebar.classList.add('open');
        cartOverlay.classList.add('open');
        cartOverlay.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    function closeCart() {
        cartSidebar.classList.remove('open');
        cartOverlay.classList.remove('open');
        setTimeout(() => {
            cartOverlay.style.display = 'none';
        }, 350);
        document.body.style.overflow = '';
    }

    // ── Cart CRUD ──
    function addItem(itemData, platform) {
        let canonical_name, products, confidence, cheaper_platform, price_diff, isExclusive = false;

        if (itemData.products) {
            // Matched pair
            canonical_name = itemData.canonical_name;
            products = itemData.products;
            confidence = itemData.confidence || 1.0;
            cheaper_platform = itemData.cheaper_platform || null;
            price_diff = itemData.price_diff || 0;
            isExclusive = false;
        } else {
            // Platform-exclusive product
            canonical_name = itemData.raw_name || itemData.name || 'Exclusive Product';
            products = { [platform]: itemData };
            confidence = 1.0;
            cheaper_platform = platform;
            price_diff = 0;
            isExclusive = true;
        }

        // Check if already in cart
        const existingIdx = cartItems.findIndex(
            item => item.canonical_name === canonical_name
        );

        if (existingIdx >= 0) {
            cartItems[existingIdx].quantity += 1;
        } else {
            cartItems.push({
                id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
                canonical_name: canonical_name,
                products: products,
                confidence: confidence,
                cheaper_platform: cheaper_platform,
                price_diff: price_diff,
                is_exclusive: isExclusive,
                exclusive_platform: isExclusive ? platform : null,
                quantity: 1,
            });
        }

        saveCart();
        updateCartUI();
        openCart();

        // Brief highlight animation
        cartToggleBtn.style.animation = 'pop-in 0.3s ease';
        setTimeout(() => { cartToggleBtn.style.animation = ''; }, 300);
    }

    function removeItem(index) {
        cartItems.splice(index, 1);
        saveCart();
        updateCartUI();
    }

    function updateQuantity(index, delta) {
        cartItems[index].quantity = Math.max(1, cartItems[index].quantity + delta);
        saveCart();
        updateCartUI();
    }

    // ── Render Cart ──
    function updateCartUI() {
        // Count badge
        const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0);
        if (totalItems > 0) {
            cartCountBadge.textContent = totalItems;
            cartCountBadge.style.display = 'flex';
        } else {
            cartCountBadge.style.display = 'none';
        }

        // Cart body
        if (cartItems.length === 0) {
            cartEmpty.style.display = 'block';
            cartItemsContainer.innerHTML = '';
            cartFooter.style.display = 'none';
            cartResult.style.display = 'none';
            return;
        }

        cartEmpty.style.display = 'none';
        cartFooter.style.display = 'block';
        cartResult.style.display = 'none';

        cartItemsContainer.innerHTML = '';
        cartItems.forEach((item, index) => {
            cartItemsContainer.appendChild(createCartItemElement(item, index));
        });
    }

    function createCartItemElement(item, index) {
        const el = document.createElement('div');
        el.className = 'cart-item';

        const platforms = Object.keys(item.products);
        const pricesHtml = platforms.map(pid => {
            const p = item.products[pid];
            if (!p || typeof p.price !== 'number') return '';
            const isWinner = pid === item.cheaper_platform;
            const color = pid === 'blinkit' ? 'var(--blinkit)' : 'var(--instamart)';
            const exclusiveTag = item.is_exclusive
                ? `<span class="badge-tag" style="font-size:0.625rem; padding:1px 5px; margin-left:6px;">${formatPlatformName(pid)} Only</span>`
                : '';
            return `
                <span class="cart-item__platform-price">
                    <span style="color:${color}; font-weight:600;">${formatPlatformName(pid)}:</span>
                    <span style="font-weight:700; ${isWinner ? 'color:var(--green)' : ''}">₹${p.price.toFixed(0)}</span>
                    ${exclusiveTag}
                </span>
            `;
        }).join('');

        el.innerHTML = `
            <div class="cart-item__top">
                <span class="cart-item__name">${escapeHtml(item.canonical_name)}</span>
                <button class="cart-item__remove" data-index="${index}" title="Remove">✕</button>
            </div>
            <div class="cart-item__prices">${pricesHtml}</div>
            <div class="cart-item__qty">
                <button class="qty-btn qty-minus" data-index="${index}">−</button>
                <span class="qty-value">${item.quantity}</span>
                <button class="qty-btn qty-plus" data-index="${index}">+</button>
            </div>
        `;

        // Event handlers
        el.querySelector('.cart-item__remove').addEventListener('click', () => removeItem(index));
        el.querySelector('.qty-minus').addEventListener('click', () => updateQuantity(index, -1));
        el.querySelector('.qty-plus').addEventListener('click', () => updateQuantity(index, 1));

        return el;
    }

    // ── Optimize ──
    async function optimizeCart() {
        optimizeBtn.disabled = true;
        optimizeBtn.textContent = '⏳ Optimizing...';

        try {
            // Build request
            const requestItems = cartItems.map(item => {
                const prices = {};
                const inStock = {};

                Object.entries(item.products).forEach(([pid, product]) => {
                    prices[pid] = product.price;
                    inStock[pid] = product.in_stock;
                });

                return {
                    id: item.id,
                    canonical_name: item.canonical_name,
                    prices,
                    in_stock: inStock,
                    quantity: item.quantity,
                };
            });

            const response = await fetch('/api/cart/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: requestItems }),
            });

            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const result = await response.json();
            renderOptimizationResult(result);
        } catch (error) {
            console.error('Optimization error:', error);
            cartResult.innerHTML = `
                <div style="color:var(--red); padding:16px; text-align:center;">
                    ❌ Optimization failed. Please try again.
                </div>
            `;
            cartResult.style.display = 'block';
        } finally {
            optimizeBtn.disabled = false;
            optimizeBtn.textContent = '⚡ Optimize Cart';
        }
    }

    function renderOptimizationResult(result) {
        let html = `<div class="cart-result__title">📊 Cart Optimization</div>`;

        // Single platform totals
        const totals = result.single_platform_totals || {};
        Object.entries(totals).forEach(([pid, breakdown]) => {
            const isRecommended = result.recommendation === `all_${pid}`;
            const recClass = isRecommended ? 'cart-result__option--recommended' : '';
            const recBadge = isRecommended ? '<span style="color:var(--green); font-size:0.7rem; font-weight:700; margin-left:8px;">✅ RECOMMENDED</span>' : '';

            html += `
                <div class="cart-result__option ${recClass}">
                    <div class="cart-result__option-label" style="color:var(--${pid})">
                        All from ${breakdown.platform_label}${recBadge}
                    </div>
                    <div class="cart-result__option-price">₹${breakdown.grand_total.toFixed(0)}</div>
                    <div class="cart-result__option-detail">
                        Items: ₹${breakdown.items_total.toFixed(0)} · 
                        Delivery: ${breakdown.delivery_cost > 0 ? '₹' + breakdown.delivery_cost.toFixed(0) : 'FREE'}
                        ${breakdown.has_oos_items ? ' · ⚠️ Some items out of stock' : ''}
                        ${breakdown.item_count < cartItems.length ? ` · ⚠️ Only ${breakdown.item_count}/${cartItems.length} items available` : ''}
                    </div>
                </div>
            `;
        });

        // Smart split
        if (result.optimal_split) {
            const split = result.optimal_split;
            const isRecommended = result.recommendation === 'split';
            const recClass = isRecommended ? 'cart-result__option--recommended' : '';
            const recBadge = isRecommended ? '<span style="color:var(--green); font-size:0.7rem; font-weight:700; margin-left:8px;">✅ RECOMMENDED</span>' : '';

            html += `
                <div class="cart-result__option ${recClass}">
                    <div class="cart-result__option-label" style="color:var(--accent-light)">
                        ⚡ Smart Split (${split.num_deliveries} deliveries)${recBadge}
                    </div>
                    <div class="cart-result__option-price">₹${split.grand_total.toFixed(0)}</div>
                    <div class="cart-result__option-detail">
                        ${Object.values(split.platform_breakdowns).map(b =>
                `${b.platform_label}: ₹${b.items_total.toFixed(0)} + ${b.delivery_cost > 0 ? '₹' + b.delivery_cost.toFixed(0) + ' delivery' : 'free delivery'}`
            ).join(' · ')}
                    </div>
                </div>
            `;
        }

        // Recommendation
        html += `
            <div class="cart-result__recommendation">
                <div class="cart-result__recommendation-title">💡 Recommendation</div>
                <div>${result.recommendation_reason}</div>
                ${result.savings_vs_worst > 0 ? `<div style="margin-top:4px; font-weight:600; color:var(--green);">You save ₹${result.savings_vs_worst.toFixed(0)} vs the most expensive option!</div>` : ''}
            </div>
        `;

        cartResult.innerHTML = html;
        cartResult.style.display = 'block';
    }

    // ── Persistence ──
    function saveCart() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cartItems));
        } catch (e) {
            console.warn('Failed to save cart:', e);
        }
    }

    function loadCart() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    }

    // ── Helpers ──
    function formatPlatformName(id) {
        const names = { blinkit: 'Blinkit', instamart: 'Instamart' };
        return names[id] || id;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Expose API ──
    window.CartManager = { addItem, removeItem, updateQuantity, getItems: () => cartItems };

    // ── Start ──
    init();
})();
