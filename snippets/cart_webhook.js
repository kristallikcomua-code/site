/**
 * Monster Webby CMS: Cart Event Webhook
 *
 * This code should be inserted into the "Third-party code" section of Monster Webby
 * It sends cart events to an n8n webhook for abandoned cart recovery and tracking
 *
 * Instructions:
 * 1. Go to Monster Webby Admin Dashboard
 * 2. Settings → Third-party Code (or Custom JS)
 * 3. Paste this code
 * 4. Update the WEBHOOK_URL with your n8n webhook URL
 * 5. Save
 */

(function() {
  'use strict';

  // Configuration - UPDATE THIS WITH YOUR N8N WEBHOOK URL
  const WEBHOOK_URL = 'https://n8n.example.com/webhook/cart-events'; // ⚠️ Change this
  const APP_KEY = 'kristallik_cart_tracker';

  /**
   * Send event to n8n webhook
   */
  function sendToWebhook(eventType, data) {
    const payload = {
      event: eventType,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...data
    };

    // Use fetch if available, otherwise fall back to XMLHttpRequest
    if (typeof fetch !== 'undefined') {
      fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        mode: 'no-cors' // Allow cross-origin
      }).catch(err => console.log('[Cart Tracker] Webhook error:', err.message));
    } else {
      // Fallback for older browsers
      const xhr = new XMLHttpRequest();
      xhr.open('POST', WEBHOOK_URL, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onload = function() {
        if (xhr.status === 200) {
          console.log('[Cart Tracker] Event sent:', eventType);
        }
      };
      xhr.onerror = function() {
        console.log('[Cart Tracker] Webhook error');
      };
      xhr.send(JSON.stringify(payload));
    }
  }

  /**
   * Extract cart data from page
   */
  function getCartData() {
    try {
      // Try to find cart data from common locations
      let cartItems = [];

      // Check if there's a global cart object
      if (typeof window.cart !== 'undefined' && window.cart) {
        cartItems = window.cart.items || window.cart.getItems?.() || [];
      }

      // Alternative: check for data attributes
      const cartElements = document.querySelectorAll('[data-cart-item]');
      if (cartElements.length > 0) {
        cartItems = Array.from(cartElements).map(el => ({
          productId: el.dataset.productId || el.getAttribute('data-product-id'),
          productName: el.dataset.productName || el.textContent?.trim(),
          price: el.dataset.price || parseFloat(el.querySelector('[data-price]')?.textContent),
          quantity: parseInt(el.dataset.quantity || 1)
        }));
      }

      return {
        itemCount: cartItems.length,
        items: cartItems.slice(0, 10), // Limit to 10 items
        totalValue: cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0)
      };
    } catch (err) {
      console.log('[Cart Tracker] Error getting cart data:', err.message);
      return { itemCount: 0, items: [], totalValue: 0 };
    }
  }

  /**
   * Track add to cart
   */
  function trackAddToCart(productId, productName, price) {
    const cartData = getCartData();
    sendToWebhook('add_to_cart', {
      productId: productId,
      productName: productName,
      price: price,
      cart: cartData
    });

    console.log('[Cart Tracker] Add to cart:', productName);
  }

  /**
   * Track cart view
   */
  function trackCartView() {
    const cartData = getCartData();
    sendToWebhook('cart_view', {
      cart: cartData
    });

    console.log('[Cart Tracker] Cart viewed');
  }

  /**
   * Track checkout initiation
   */
  function trackCheckoutStart() {
    const cartData = getCartData();
    sendToWebhook('checkout_started', {
      cart: cartData
    });

    console.log('[Cart Tracker] Checkout started');
  }

  /**
   * Track purchase
   */
  function trackPurchase(orderId, cartData) {
    sendToWebhook('purchase', {
      orderId: orderId,
      cart: cartData
    });

    console.log('[Cart Tracker] Purchase completed');
  }

  /**
   * Hook into page events
   */
  function initializeTracking() {
    // Listen for add to cart button clicks
    document.addEventListener('click', function(e) {
      const addToCartBtn = e.target.closest('[class*="add-to-cart"], [class*="add-cart"], button[data-action="addToCart"]');
      if (addToCartBtn) {
        const productId = addToCartBtn.dataset.productId || addToCartBtn.getAttribute('data-id');
        const productName = addToCartBtn.dataset.productName || document.querySelector('[data-product-name]')?.textContent;
        const price = addToCartBtn.dataset.price || parseFloat(document.querySelector('[data-price]')?.textContent);
        trackAddToCart(productId, productName, price);
      }
    });

    // Track cart page views
    if (window.location.pathname.includes('/cart') || document.querySelector('[data-page="cart"]')) {
      trackCartView();
    }

    // Track checkout initiation
    document.addEventListener('click', function(e) {
      const checkoutBtn = e.target.closest('[class*="checkout"], button[data-action="checkout"]');
      if (checkoutBtn) {
        trackCheckoutStart();
      }
    });
  }

  // Initialize on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTracking);
  } else {
    initializeTracking();
  }

  // Expose functions globally for manual tracking if needed
  window.kartTracker = {
    addToCart: trackAddToCart,
    cartView: trackCartView,
    checkoutStart: trackCheckoutStart,
    purchase: trackPurchase,
    getCartData: getCartData
  };

  console.log('[Cart Tracker] Initialized');
})();
