/**
 * Cookie Consent Manager
 * Handles GDPR/CCPA compliant cookie consent for EMMA.STUDIO
 */

class CookieConsentManager {
    constructor() {
        this.consentKey = 'emma_cookie_consent';
        this.preferencesKey = 'emma_cookie_preferences';
        this.consentVersion = '1.0';
        this.banner = null;
        this.settingsModal = null;
        this.preferences = this.getPreferences();
        
        this.init();
    }

    init() {
        this.createBanner();
        this.createSettingsModal();
        this.checkConsent();
        this.bindEvents();
    }

    getPreferences() {
        const stored = localStorage.getItem(this.preferencesKey);
        if (stored) {
            return JSON.parse(stored);
        }
        // Default preferences
        return {
            necessary: true,
            functional: false,
            analytics: false,
            marketing: false,
            version: this.consentVersion
        };
    }

    savePreferences(preferences) {
        this.preferences = { ...this.preferences, ...preferences, version: this.consentVersion };
        localStorage.setItem(this.preferencesKey, JSON.stringify(this.preferences));
        localStorage.setItem(this.consentKey, JSON.stringify({
            consented: true,
            timestamp: new Date().toISOString(),
            version: this.consentVersion
        }));
        this.applyPreferences();
    }

    hasConsented() {
        const consent = localStorage.getItem(this.consentKey);
        if (!consent) return false;
        
        const parsed = JSON.parse(consent);
        // Check if consent version matches current version
        if (parsed.version !== this.consentVersion) {
            return false; // Re-consent needed for new version
        }
        return parsed.consented;
    }

    checkConsent() {
        if (!this.hasConsented()) {
            this.showBanner();
        } else {
            this.applyPreferences();
        }
    }

    showBanner() {
        if (this.banner) {
            this.banner.style.display = 'flex';
        }
    }

    hideBanner() {
        if (this.banner) {
            this.banner.style.display = 'none';
        }
    }

    acceptAll() {
        this.savePreferences({
            necessary: true,
            functional: true,
            analytics: true,
            marketing: true
        });
        this.hideBanner();
    }

    acceptNecessary() {
        this.savePreferences({
            necessary: true,
            functional: false,
            analytics: false,
            marketing: false
        });
        this.hideBanner();
    }

    applyPreferences() {
        // Apply cookie preferences
        document.body.dataset.cookieConsent = JSON.stringify(this.preferences);
        
        // Dispatch custom event for other scripts to listen
        window.dispatchEvent(new CustomEvent('cookieConsentChanged', {
            detail: this.preferences
        }));

        // Enable/disable tracking based on preferences
        if (!this.preferences.analytics) {
            this.disableAnalytics();
        }
        if (!this.preferences.marketing) {
            this.disableMarketing();
        }
    }

    disableAnalytics() {
        // Disable analytics cookies/tracking
        window['ga-disable-GA_MEASUREMENT_ID'] = true;
        console.log('Analytics cookies disabled');
    }

    disableMarketing() {
        // Disable marketing cookies/tracking
        console.log('Marketing cookies disabled');
    }

    createBanner() {
        if (document.getElementById('cookie-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'cookie-banner';
        banner.innerHTML = `
            <div class="cookie-banner-content">
                <div class="cookie-banner-text">
                    <h3>🍪 Cookie Preferences</h3>
                    <p>We use cookies to enhance your experience. By continuing to visit this site you agree to our use of cookies.</p>
                    <a href="/cookie-policy" class="cookie-link">Learn more in our Cookie Policy</a>
                </div>
                <div class="cookie-banner-buttons">
                    <button class="cookie-btn cookie-btn-settings" id="cookieSettings">Customize</button>
                    <button class="cookie-btn cookie-btn-accept" id="cookieAcceptAll">Accept All</button>
                    <button class="cookie-btn cookie-btn-reject" id="cookieReject">Necessary Only</button>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #cookie-banner {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: linear-gradient(135deg, #0a192f 0%, #1a365d 100%);
                border-top: 2px solid #00f2fe;
                padding: 20px;
                z-index: 10000;
                display: none;
                box-shadow: 0 -4px 20px rgba(0, 242, 254, 0.2);
                animation: slideUp 0.5s ease;
            }
            
            @keyframes slideUp {
                from { transform: translateY(100%); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            .cookie-banner-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
            }
            
            .cookie-banner-text {
                flex: 1;
                color: #e2e8f0;
            }
            
            .cookie-banner-text h3 {
                margin: 0 0 10px 0;
                color: #00f2fe;
                font-family: 'Rajdhani', sans-serif;
                font-size: 18px;
            }
            
            .cookie-banner-text p {
                margin: 0 0 10px 0;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .cookie-link {
                color: #00f2fe;
                text-decoration: none;
                font-size: 13px;
                border-bottom: 1px dashed #00f2fe;
            }
            
            .cookie-link:hover {
                color: #fff;
                border-bottom-color: #fff;
            }
            
            .cookie-banner-buttons {
                display: flex;
                gap: 10px;
                flex-shrink: 0;
            }
            
            .cookie-btn {
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                font-size: 14px;
                transition: all 0.3s ease;
                font-family: 'Rajdhani', sans-serif;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .cookie-btn-settings {
                background: transparent;
                border: 1px solid #00f2fe;
                color: #00f2fe;
            }
            
            .cookie-btn-settings:hover {
                background: rgba(0, 242, 254, 0.1);
            }
            
            .cookie-btn-accept {
                background: linear-gradient(135deg, #00f2fe, #0072ff);
                color: #0a192f;
            }
            
            .cookie-btn-accept:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0, 242, 254, 0.4);
            }
            
            .cookie-btn-reject {
                background: rgba(255, 255, 255, 0.1);
                color: #e2e8f0;
            }
            
            .cookie-btn-reject:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            
            @media (max-width: 768px) {
                .cookie-banner-content {
                    flex-direction: column;
                    text-align: center;
                }
                
                .cookie-banner-buttons {
                    flex-wrap: wrap;
                    justify-content: center;
                }
                
                .cookie-btn {
                    flex: 1;
                    min-width: 120px;
                }
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(banner);
        this.banner = banner;
    }

    createSettingsModal() {
        if (document.getElementById('cookie-settings-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'cookie-settings-modal';
        modal.innerHTML = `
            <div class="cookie-modal-overlay" id="cookieModalOverlay"></div>
            <div class="cookie-modal-content">
                <div class="cookie-modal-header">
                    <h2>Cookie Settings</h2>
                    <button class="cookie-modal-close" id="cookieModalClose">&times;</button>
                </div>
                <div class="cookie-modal-body">
                    <div class="cookie-category">
                        <div class="cookie-category-header">
                            <div class="cookie-category-info">
                                <h3>Necessary Cookies</h3>
                                <p>Required for the website to function properly. Cannot be disabled.</p>
                            </div>
                            <label class="cookie-toggle">
                                <input type="checkbox" checked disabled>
                                <span class="cookie-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="cookie-category">
                        <div class="cookie-category-header">
                            <div class="cookie-category-info">
                                <h3>Functional Cookies</h3>
                                <p>Enable enhanced features like personalization and remembering your preferences.</p>
                            </div>
                            <label class="cookie-toggle">
                                <input type="checkbox" id="functionalCookies" ${this.preferences.functional ? 'checked' : ''}>
                                <span class="cookie-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="cookie-category">
                        <div class="cookie-category-header">
                            <div class="cookie-category-info">
                                <h3>Analytics Cookies</h3>
                                <p>Help us improve the website by collecting anonymous usage data.</p>
                            </div>
                            <label class="cookie-toggle">
                                <input type="checkbox" id="analyticsCookies" ${this.preferences.analytics ? 'checked' : ''}>
                                <span class="cookie-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="cookie-category">
                        <div class="cookie-category-header">
                            <div class="cookie-category-info">
                                <h3>Marketing Cookies</h3>
                                <p>Used to deliver relevant advertisements and track marketing campaigns.</p>
                            </div>
                            <label class="cookie-toggle">
                                <input type="checkbox" id="marketingCookies" ${this.preferences.marketing ? 'checked' : ''}>
                                <span class="cookie-slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
                <div class="cookie-modal-footer">
                    <button class="cookie-btn cookie-btn-reject" id="cookieRejectAll">Reject All</button>
                    <button class="cookie-btn cookie-btn-accept" id="cookieSavePreferences">Save Preferences</button>
                </div>
            </div>
        `;

        // Add modal styles
        const style = document.createElement('style');
        style.textContent = `
            #cookie-settings-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 10001;
            }
            
            .cookie-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(5px);
            }
            
            .cookie-modal-content {
                position: relative;
                background: linear-gradient(135deg, #0a192f 0%, #1a365d 100%);
                border: 2px solid #00f2fe;
                border-radius: 16px;
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                margin: 5% auto;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 242, 254, 0.3);
            }
            
            .cookie-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 25px;
                border-bottom: 1px solid rgba(0, 242, 254, 0.2);
            }
            
            .cookie-modal-header h2 {
                margin: 0;
                color: #00f2fe;
                font-family: 'Rajdhani', sans-serif;
                font-size: 24px;
            }
            
            .cookie-modal-close {
                background: none;
                border: none;
                color: #e2e8f0;
                font-size: 32px;
                cursor: pointer;
                line-height: 1;
                padding: 0;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                transition: all 0.3s ease;
            }
            
            .cookie-modal-close:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #00f2fe;
            }
            
            .cookie-modal-body {
                padding: 25px;
            }
            
            .cookie-category {
                margin-bottom: 25px;
                padding-bottom: 25px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .cookie-category:last-child {
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }
            
            .cookie-category-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 20px;
            }
            
            .cookie-category-info h3 {
                margin: 0 0 8px 0;
                color: #fff;
                font-family: 'Rajdhani', sans-serif;
                font-size: 18px;
            }
            
            .cookie-category-info p {
                margin: 0;
                color: #94a3b8;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .cookie-toggle {
                position: relative;
                display: inline-block;
                width: 50px;
                height: 26px;
                flex-shrink: 0;
            }
            
            .cookie-toggle input {
                opacity: 0;
                width: 0;
                height: 0;
            }
            
            .cookie-slider {
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(255, 255, 255, 0.2);
                transition: 0.4s;
                border-radius: 26px;
            }
            
            .cookie-slider:before {
                position: absolute;
                content: "";
                height: 20px;
                width: 20px;
                left: 3px;
                bottom: 3px;
                background-color: white;
                transition: 0.4s;
                border-radius: 50%;
            }
            
            .cookie-toggle input:checked + .cookie-slider {
                background: linear-gradient(135deg, #00f2fe, #0072ff);
            }
            
            .cookie-toggle input:checked + .cookie-slider:before {
                transform: translateX(24px);
            }
            
            .cookie-toggle input:disabled + .cookie-slider {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .cookie-modal-footer {
                display: flex;
                justify-content: flex-end;
                gap: 15px;
                padding: 25px;
                border-top: 1px solid rgba(0, 242, 254, 0.2);
            }
            
            @media (max-width: 768px) {
                .cookie-modal-content {
                    margin: 10% auto;
                    width: 95%;
                }
                
                .cookie-category-header {
                    flex-direction: column;
                }
                
                .cookie-toggle {
                    align-self: flex-start;
                }
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(modal);
        this.settingsModal = modal;
    }

    showSettings() {
        if (this.settingsModal) {
            this.settingsModal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    hideSettings() {
        if (this.settingsModal) {
            this.settingsModal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    bindEvents() {
        // Banner buttons
        const acceptAllBtn = document.getElementById('cookieAcceptAll');
        const rejectBtn = document.getElementById('cookieReject');
        const settingsBtn = document.getElementById('cookieSettings');

        if (acceptAllBtn) {
            acceptAllBtn.addEventListener('click', () => this.acceptAll());
        }
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.acceptNecessary());
        }
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.hideBanner();
                this.showSettings();
            });
        }

        // Modal events
        const modalClose = document.getElementById('cookieModalClose');
        const modalOverlay = document.getElementById('cookieModalOverlay');
        const saveBtn = document.getElementById('cookieSavePreferences');
        const rejectAllBtn = document.getElementById('cookieRejectAll');

        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideSettings());
        }
        if (modalOverlay) {
            modalOverlay.addEventListener('click', () => this.hideSettings());
        }
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const functional = document.getElementById('functionalCookies').checked;
                const analytics = document.getElementById('analyticsCookies').checked;
                const marketing = document.getElementById('marketingCookies').checked;
                
                this.savePreferences({ functional, analytics, marketing });
                this.hideSettings();
                this.hideBanner();
            });
        }
        if (rejectAllBtn) {
            rejectAllBtn.addEventListener('click', () => {
                this.acceptNecessary();
                this.hideSettings();
            });
        }

        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.settingsModal && this.settingsModal.style.display === 'block') {
                this.hideSettings();
            }
        });
    }
}

// Initialize cookie consent manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.cookieConsent = new CookieConsentManager();
    });
} else {
    window.cookieConsent = new CookieConsentManager();
}

// Global function to open settings from anywhere git config --list
window.openCookieSettings = function() {
    if (window.cookieConsent) {
        window.cookieConsent.showSettings();
    }
};
