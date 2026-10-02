/**
 * Stock Market Data Analyzer — Executive Dashboard Client Presentation Logic
 * Task 8.4: docs/app.js
 *
 * Adheres strictly to the frozen specification:
 * - Pure rendering layer: ZERO client-side financial recalculations
 * - Reads precomputed data exclusively from window.STOCK_DASHBOARD_DATA
 * - Interactive instrument slicer, date range presets, indicator overlay toggles, reset filters
 * - Synchronized time-series zoom and filter interactions across all tabs
 * - Formats currency in ₹ (equities) and pts (^NSEI), percentages with 2 decimals, volume in Indian numbering
 * - Accessible, responsive Plotly.js charts with PowerBI corporate financial styling
 * - Executive 3-Tab Architecture with responsive Plotly resize handlers
 */

document.addEventListener('DOMContentLoaded', () => {
    const data = window.STOCK_DASHBOARD_DATA;
    if (!data) {
        console.error("STOCK_DASHBOARD_DATA not found. Make sure dashboard_data.js is loaded.");
        return;
    }

    // Instrument Color Theme Palette (matching style.css design system)
    const COLORS = {
        'RELIANCE.NS': '#0284c7', // Corporate Blue
        'TCS.NS':      '#4338ca', // Indian Indigo
        'INFY.NS':     '#0d9488', // Emerald Teal
        'SBIN.NS':     '#d97706', // Warm Amber
        'ICICIBANK.NS':'#dc2626', // Rust Crimson
        '^NSEI':       '#475569'  // Neutral Slate (Benchmark)
    };

    const CSS_CLASS = {
        'RELIANCE.NS': 'reliance',
        'TCS.NS':      'tcs',
        'INFY.NS':     'infy',
        'SBIN.NS':     'sbin',
        'ICICIBANK.NS':'icicibank',
        '^NSEI':       'nsei'
    };

    const DISPLAY_NAMES = {
        'RELIANCE.NS': 'Reliance Industries',
        'TCS.NS':      'Tata Consultancy Services',
        'INFY.NS':     'Infosys Limited',
        'SBIN.NS':     'State Bank of India',
        'ICICIBANK.NS':'ICICI Bank',
        '^NSEI':       'NIFTY 50 Benchmark Index'
    };

    // Time-series charts that respond to the global Date Range slicer
    const TIME_SERIES_CHART_IDS = [
        'chart-normalized',
        'chart-price',
        'chart-rsi',
        'chart-volume',
        'chart-drawdown',
        'chart-volatility'
    ];

    // Global Plotly Configuration
    const PLOTLY_CONFIG = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
    };

    // Shared Plotly Layout Defaults
    const LAYOUT_DEFAULTS = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#ffffff',
        font: {
            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            color: '#0f172a',
            size: 12
        },
        margin: { t: 25, r: 20, b: 40, l: 55 },
        legend: {
            orientation: 'h',
            y: -0.16,
            x: 0.5,
            xanchor: 'center',
            font: { size: 11 }
        },
        xaxis: {
            type: 'date',
            gridcolor: '#f1f5f9',
            linecolor: '#e2e8f0',
            zerolinecolor: '#f1f5f9',
            tickfont: { size: 11, color: '#64748b' }
        },
        yaxis: {
            type: 'linear',
            gridcolor: '#f1f5f9',
            linecolor: '#e2e8f0',
            zerolinecolor: '#f1f5f9',
            tickfont: { size: 11, color: '#64748b' }
        },
        hovermode: 'x unified'
    };

    // -------------------------------------------------------------------------
    // Number Formatting Helpers (Indian Locale & Financial Conventions)
    // -------------------------------------------------------------------------
    const formatIndianNumber = (num, decimals = 2) => {
        if (num === null || num === undefined || isNaN(num)) return '-';
        return Number(num).toLocaleString('en-IN', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    };

    const formatPrice = (value, ticker) => {
        if (value === null || value === undefined || isNaN(value)) return '-';
        if (ticker === '^NSEI') {
            return formatIndianNumber(value, 2) + ' pts';
        } else {
            return '₹' + formatIndianNumber(value, 2);
        }
    };

    const formatPct = (value) => {
        if (value === null || value === undefined || isNaN(value)) return '-';
        const num = Number(value);
        const sign = num > 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}%`;
    };

    const formatRatio = (value) => {
        if (value === null || value === undefined || isNaN(value)) return '-';
        const num = Number(value);
        const sign = num > 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}`;
    };

    const formatVolume = (val) => {
        if (val === null || val === undefined || isNaN(val)) return '-';
        const n = Number(val);
        if (n >= 10000000) return (n / 10000000).toFixed(2) + ' Cr';
        if (n >= 100000) return (n / 100000).toFixed(2) + ' L';
        if (n >= 1000) return (n / 1000).toFixed(1) + ' K';
        return n.toLocaleString('en-IN');
    };

    // Global State Variables
    let selectedInstrument = 'RELIANCE.NS';
    let selectedDateRange = '5Y';
    let currentXRange = null;

    // -------------------------------------------------------------------------
    // Initialization Lifecycle
    // -------------------------------------------------------------------------
    function showPlotlyOfflineNotice() {
        const banner = document.getElementById('provenance-banner');
        if (banner) {
            const notice = document.createElement('div');
            notice.className = 'provenance-banner__pill';
            notice.style.backgroundColor = '#fef2f2';
            notice.style.borderColor = '#f87171';
            notice.style.color = '#991b1b';
            notice.style.fontWeight = '500';
            notice.innerHTML = '⚠️ <strong>Offline Notice:</strong> Plotly CDN unavailable. Interactive charts require an active internet connection to load from CDN. Tabular metrics and KPI scorecards remain functional.';
            banner.prepend(notice);
        }
        document.querySelectorAll('.chart-container__plot').forEach(plot => {
            plot.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;font-size:13px;padding:24px;text-align:center;">Interactive chart unavailable offline (Plotly CDN not loaded).</div>';
        });
    }

    function init() {
        populateMetadata();
        populateProvenance();
        buildKPICards();
        buildSummaryTable();

        setupTabNavigation();
        setupInstrumentSlicer();
        setupDateSlicer();
        setupOverlayToggles();
        setupTableSorting();
        setupResetButton();

        // Initialize 5Y date boundaries
        computeDateRange('5Y');

        // Lightweight Plotly availability guard
        if (typeof Plotly === 'undefined') {
            console.warn("Plotly library not detected. CDN script may be blocked or offline.");
            showPlotlyOfflineNotice();
            return;
        }

        renderAllCharts();
        updateSelectedInstrumentUI();
    }

    // -------------------------------------------------------------------------
    // 1. Metadata & Temporal Tags Population (Compact & Consolidated)
    // -------------------------------------------------------------------------
    function populateMetadata() {
        const metaContainer = document.getElementById('header-meta');
        if (!metaContainer) return;

        const m = data.metadata;
        const obsDate = m.market_data_last_observation_date || '2026-09-25';
        const runTime = m.pipeline_execution_timestamp || new Date().toISOString();
        const dateRangeStr = m.date_range ? `${m.date_range.actual_first_observation} to ${m.date_range.actual_last_observation}` : '2021-09-28 to 2026-09-25';

        metaContainer.innerHTML = `
            <div class="dashboard-header__meta-tag">
                <span class="dashboard-header__meta-tag--label">Session:</span>
                <span class="mono">${obsDate}</span>
            </div>
            <div class="dashboard-header__meta-tag">
                <span class="dashboard-header__meta-tag--label">Run (UTC):</span>
                <span class="mono">${runTime.replace('T', ' ').substring(0, 19)}Z</span>
            </div>
            <div class="dashboard-header__meta-tag">
                <span class="dashboard-header__meta-tag--label">Horizon:</span>
                <span class="mono">${dateRangeStr}</span>
            </div>
            <div class="dashboard-header__meta-tag">
                <span class="dashboard-header__meta-tag--label">Methodology:</span>
                <span class="mono">v${m.methodology_version || '2026.1'}</span>
            </div>
            <div class="dashboard-header__meta-tag">
                <span class="dashboard-header__meta-tag--label">Schema:</span>
                <span class="mono">v${m.schema_version || '1.0.0'}</span>
            </div>
        `;
    }

    // -------------------------------------------------------------------------
    // 2. Data Provenance Banner Population (Consolidated & Clean)
    // -------------------------------------------------------------------------
    function populateProvenance() {
        const banner = document.getElementById('provenance-banner');
        if (!banner) return;

        const m = data.metadata;
        const rfDesc = (m.risk_free_proxy && m.risk_free_proxy.description)
            ? m.risk_free_proxy.description
            : 'Illustrative proxy assumption representing 10-Yr Indian G-Sec yield';
        const rfAnnual = (m.risk_free_proxy && m.risk_free_proxy.annual_rate)
            ? (m.risk_free_proxy.annual_rate * 100).toFixed(2) + '%'
            : '6.50%';

        banner.innerHTML = `
            <div class="provenance-banner__pill">
                <span class="provenance-banner__pill--label">Provenance:</span>
                <span class="provenance-banner__pill--value">${m.provenance_reference || 'data/processed/{TICKER}_engineered.csv (Local provenance only)'}</span>
            </div>
            <div class="provenance-banner__pill">
                <span class="provenance-banner__pill--label">Risk-Free Rate:</span>
                <span class="provenance-banner__pill--value">10-Yr Indian G-Sec @ ${rfAnnual} p.a. (${rfDesc})</span>
            </div>
            <div class="provenance-banner__pill">
                <span class="provenance-banner__pill--label">Architecture:</span>
                <span class="provenance-banner__pill--value">Static GitHub Pages — 100% Client-Side Rendering</span>
            </div>
        `;
    }

    // -------------------------------------------------------------------------
    // 3. PowerBI Executive Tab Navigation
    // -------------------------------------------------------------------------
    function setupTabNavigation() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTabId = btn.getAttribute('data-tab');
                switchTab(targetTabId);
            });
        });
    }

    function switchTab(targetTabId) {
        // 1. Update button active states and ARIA attributes
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            const isActive = btn.getAttribute('data-tab') === targetTabId;
            btn.classList.toggle('tab-btn--active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        // 2. Toggle panes and trigger Plotly reflow for newly unhidden pane
        const tabPanes = document.querySelectorAll('.tab-pane');
        tabPanes.forEach(pane => {
            const isTarget = pane.id === targetTabId;
            pane.classList.toggle('tab-pane--hidden', !isTarget);
            if (isTarget) {
                // Re-render plots for the newly visible tab to ensure flawless axis layout & dimensions
                if (targetTabId === 'tab-overview') {
                    renderNormalizedChart();
                    renderScatterChart();
                    render52wChart();
                } else if (targetTabId === 'tab-technical') {
                    renderPriceChart();
                    renderRsiChart();
                    renderVolumeChart();
                } else if (targetTabId === 'tab-risk') {
                    renderDrawdownChart();
                    renderVolatilityChart();
                    renderCorrelationChart();
                }

                const syncAndResizePlots = () => {
                    pane.querySelectorAll('.chart-container__plot').forEach(plot => {
                        if (plot && plot.data) {
                            try {
                                Plotly.Plots.resize(plot);
                                // Ensure time-series charts in this pane strictly reflect active date range
                                if (TIME_SERIES_CHART_IDS.includes(plot.id)) {
                                    const update = (selectedDateRange === '5Y')
                                        ? { 'xaxis.autorange': true }
                                        : { 'xaxis.range': currentXRange, 'xaxis.autorange': false };
                                    Plotly.relayout(plot, update);
                                }
                            } catch (e) {
                                console.warn("Plotly sync/resize error:", e);
                            }
                        }
                    });
                };
                requestAnimationFrame(syncAndResizePlots);
                setTimeout(syncAndResizePlots, 60);
            }
        });
    }

    // -------------------------------------------------------------------------
    // 4. KPI Scorecards Generation (4 Focused Cards for Selected Instrument & Active Period)
    // -------------------------------------------------------------------------
    function buildKPICards() {
        const grid = document.getElementById('kpi-grid');
        if (!grid) return;

        const ticker = selectedInstrument;
        const period = selectedDateRange || '5Y';

        // 1. Fixed-definition metrics (Always derived from full record / latest market observation)
        const summary5Y = data.summary_metrics.find(m => m.ticker === ticker);
        if (!summary5Y) return;

        // 2. Period-specific metrics (Look for precomputed period metrics in schema)
        let periodMetrics = null;
        if (data.period_metrics && data.period_metrics[period] && data.period_metrics[period][ticker]) {
            periodMetrics = data.period_metrics[period][ticker];
        } else if (period === '5Y') {
            periodMetrics = summary5Y;
        }

        const isBenchmark = ticker === '^NSEI';
        const cls = CSS_CLASS[ticker] || 'nsei';

        // Fixed-definition values (Preserved across all date presets)
        const lastClosePrice = formatPrice(summary5Y.last_close, ticker);
        const w52Low = formatPrice(summary5Y['52w_low'], ticker);
        const w52High = formatPrice(summary5Y['52w_high'], ticker);

        // Date-sensitive metrics & labels
        const periodTitle = period === '5Y' ? '5-Year' : (period === '3Y' ? '3-Year' : (period === '1Y' ? '1-Year' : 'YTD'));
        const hasPeriodData = periodMetrics !== null;

        const cagrVal = hasPeriodData ? formatPct(periodMetrics.cagr_pct) : '–';
        const cagrValueCls = (hasPeriodData && periodMetrics.cagr_pct >= 0) ? 'cell--positive' : (hasPeriodData ? 'cell--negative' : 'cell--muted');

        const volVal = hasPeriodData ? (periodMetrics.annualized_volatility_pct ? periodMetrics.annualized_volatility_pct.toFixed(2) + '%' : '-') : '–';

        const sharpeVal = hasPeriodData ? formatRatio(periodMetrics.sharpe_ratio) : '–';
        const sharpeCls = hasPeriodData
            ? (periodMetrics.sharpe_ratio >= 1.0 ? 'badge--positive' : (periodMetrics.sharpe_ratio > 0 ? 'badge--neutral' : 'badge--negative'))
            : 'badge--neutral';

        const mddVal = hasPeriodData ? formatPct(periodMetrics.max_drawdown_pct) : '–';
        const betaVal = isBenchmark ? '1.00 (Benchmark)' : (hasPeriodData ? formatRatio(periodMetrics.beta_nifty) : '–');
        const var95Val = (hasPeriodData && periodMetrics.var_95_pct !== undefined && periodMetrics.var_95_pct !== null)
            ? formatPct(periodMetrics.var_95_pct)
            : ((summary5Y.var_95_pct !== undefined && summary5Y.var_95_pct !== null) ? formatPct(summary5Y.var_95_pct) : '–');

        grid.innerHTML = `
            <!-- Card 1: Last Close / Index Level + 52-Week Range Corridor (Fixed Definitions) -->
            <div class="kpi-card kpi-card--${cls}">
                <div class="kpi-card__ticker">
                    <span>${ticker}</span>
                    ${isBenchmark ? '<span class="badge badge--neutral">Benchmark</span>' : ''}
                </div>
                <div class="kpi-card__name">${DISPLAY_NAMES[ticker]}</div>
                <div class="kpi-card__value mono">${lastClosePrice}</div>
                <div class="kpi-card__label">${isBenchmark ? 'Index Level' : 'Last Close'}</div>
                <div class="kpi-card__range">
                    <div class="kpi-card__range-item">
                        <span class="kpi-card__range-label">52W L:</span>
                        <span class="kpi-card__range-val">${w52Low}</span>
                    </div>
                    <div class="kpi-card__range-item">
                        <span class="kpi-card__range-label">52W H:</span>
                        <span class="kpi-card__range-val">${w52High}</span>
                    </div>
                </div>
            </div>

            <!-- Card 2: Period CAGR + Beta vs NIFTY (Date-Sensitive) -->
            <div class="kpi-card kpi-card--${cls}">
                <div class="kpi-card__ticker">
                    <span>${periodTitle} CAGR</span>
                </div>
                <div class="kpi-card__name">Compound Annual Growth Rate</div>
                <div class="kpi-card__value mono ${cagrValueCls}">${cagrVal}</div>
                <div class="kpi-card__label">Annualized Return (${period})</div>
                <div class="kpi-card__secondary">
                    <span class="kpi-card__secondary-label">Beta vs NIFTY:</span>
                    <span class="kpi-card__secondary-value mono">${betaVal}</span>
                </div>
            </div>

            <!-- Card 3: Annualized Volatility + Sharpe Ratio (Date-Sensitive) -->
            <div class="kpi-card kpi-card--${cls}">
                <div class="kpi-card__ticker">
                    <span>Ann. Volatility</span>
                </div>
                <div class="kpi-card__name">Historical Return Dispersion (${period})</div>
                <div class="kpi-card__value mono">${volVal}</div>
                <div class="kpi-card__label">Annual Standard Deviation (${period})</div>
                <div class="kpi-card__secondary">
                    <span class="kpi-card__secondary-label">Sharpe (Rf=6.5%):</span>
                    <span class="kpi-card__secondary-value badge ${sharpeCls}">${sharpeVal}</span>
                </div>
            </div>

            <!-- Card 4: Maximum Drawdown + Historical VaR 95% (Date-Sensitive) -->
            <div class="kpi-card kpi-card--${cls}">
                <div class="kpi-card__ticker">
                    <span>Max Drawdown</span>
                </div>
                <div class="kpi-card__name">Peak-to-Trough Decline (${period})</div>
                <div class="kpi-card__value mono cell--negative">${mddVal}</div>
                <div class="kpi-card__label">Worst Capital Retracement (${period})</div>
                <div class="kpi-card__secondary">
                    <span class="kpi-card__secondary-label">Historical VaR (95%):</span>
                    <span class="kpi-card__secondary-value mono cell--negative">${var95Val}</span>
                </div>
            </div>
        `;
    }

    // -------------------------------------------------------------------------
    // Canonical Executive Table Order: NIFTY 50 Benchmark first, followed by the five equities
    const CANONICAL_TABLE_ORDER = [
        '^NSEI',
        'RELIANCE.NS',
        'TCS.NS',
        'INFY.NS',
        'SBIN.NS',
        'ICICIBANK.NS'
    ];

    function getCanonicalSummaryMetrics(period = selectedDateRange) {
        if (!data.summary_metrics) return [];
        const orderMap = new Map(CANONICAL_TABLE_ORDER.map((ticker, idx) => [ticker, idx]));
        const sorted5Y = [...data.summary_metrics].sort((a, b) => {
            const idxA = orderMap.has(a.ticker) ? orderMap.get(a.ticker) : 999;
            const idxB = orderMap.has(b.ticker) ? orderMap.get(b.ticker) : 999;
            return idxA - idxB;
        });

        if (period === '5Y' || !data.period_metrics || !data.period_metrics[period]) {
            return sorted5Y;
        }

        const pMetrics = data.period_metrics[period];
        return sorted5Y.map(base => {
            const pm = pMetrics[base.ticker];
            if (!pm) return base;
            return {
                ...base,
                annualized_volatility_pct: pm.annualized_volatility_pct !== undefined ? pm.annualized_volatility_pct : base.annualized_volatility_pct,
                sharpe_ratio: pm.sharpe_ratio !== undefined ? pm.sharpe_ratio : base.sharpe_ratio,
                max_drawdown_pct: pm.max_drawdown_pct !== undefined ? pm.max_drawdown_pct : base.max_drawdown_pct,
                var_95_pct: pm.var_95_pct !== undefined ? pm.var_95_pct : base.var_95_pct,
                beta_nifty: pm.beta_nifty !== undefined ? pm.beta_nifty : base.beta_nifty
            };
        });
    }

    function updateSummaryTableHeaders(period = selectedDateRange) {
        const table = document.getElementById('summary-table');
        if (!table) return;
        const pTag = period || '5Y';
        const volTh = table.querySelector('th[data-sort="annualized_volatility_pct"]');
        if (volTh) volTh.textContent = `Ann. Volatility (${pTag}) (%)`;
        const sharpeTh = table.querySelector('th[data-sort="sharpe_ratio"]');
        if (sharpeTh) sharpeTh.textContent = `Sharpe (${pTag})`;
        const mddTh = table.querySelector('th[data-sort="max_drawdown_pct"]');
        if (mddTh) mddTh.textContent = `Max Drawdown (${pTag}) (%)`;
        const varTh = table.querySelector('th[data-sort="var_95_pct"]');
        if (varTh) varTh.textContent = `VaR 95% (${pTag}) (%)`;
        const betaTh = table.querySelector('th[data-sort="beta_nifty"]');
        if (betaTh) betaTh.textContent = `Beta vs NIFTY (${pTag})`;
    }

    // -------------------------------------------------------------------------
    // 5. Master Comparative Performance Table (Benchmark-First Ordering)
    // -------------------------------------------------------------------------
    function buildSummaryTable() {
        const tbody = document.getElementById('summary-table-body');
        if (!tbody) return;
        updateSummaryTableHeaders(selectedDateRange);
        renderTableRows(getCanonicalSummaryMetrics(selectedDateRange));
    }

    function renderTableRows(metricsArray) {
        const tbody = document.getElementById('summary-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        // Compute best/worst values for highlighting
        const validCagr = metricsArray.map(m => m.cagr_pct).filter(v => v !== null && !isNaN(v));
        const maxCagr = Math.max(...validCagr);
        const minCagr = Math.min(...validCagr);

        const validSharpe = metricsArray.map(m => m.sharpe_ratio).filter(v => v !== null && !isNaN(v));
        const maxSharpe = Math.max(...validSharpe);
        const minSharpe = Math.min(...validSharpe);

        const validDD = metricsArray.map(m => m.max_drawdown_pct).filter(v => v !== null && !isNaN(v));
        const worstDD = Math.min(...validDD);

        metricsArray.forEach(m => {
            const isBenchmark = m.ticker === '^NSEI';
            const rowCls = isBenchmark ? 'tr--benchmark' : '';

            // Cell class logic
            const cagrBestWorst = m.cagr_pct === maxCagr ? 'cell--best' : (m.cagr_pct === minCagr ? 'cell--worst' : (m.cagr_pct >= 0 ? 'cell--positive' : 'cell--negative'));
            const sharpeBestWorst = m.sharpe_ratio === maxSharpe ? 'cell--best' : (m.sharpe_ratio === minSharpe ? 'cell--worst' : '');
            const ddBestWorst = m.max_drawdown_pct === worstDD ? 'cell--worst' : 'cell--negative';

            const betaText = isBenchmark ? '1.00 (Benchmark)' : formatRatio(m.beta_nifty);

            tbody.innerHTML += `
                <tr class="${rowCls}">
                    <td class="td-instrument">
                        <div class="instrument-cell">
                            <span class="instrument-dot instrument-dot--${CSS_CLASS[m.ticker] || 'nsei'}"></span>
                            <div>
                                <span class="instrument-ticker">${m.ticker}</span>
                                ${isBenchmark ? '<span class="badge badge--neutral badge--xs">Benchmark</span>' : ''}
                                <div class="instrument-name">${DISPLAY_NAMES[m.ticker]}</div>
                            </div>
                        </div>
                    </td>
                    <td class="mono font-semibold">${formatPrice(m.last_close, m.ticker)}</td>
                    <td class="mono ${cagrBestWorst}">${formatPct(m.cagr_pct)}</td>
                    <td class="mono">${m.annualized_volatility_pct ? m.annualized_volatility_pct.toFixed(2) + '%' : '-'}</td>
                    <td class="mono ${sharpeBestWorst}">${formatRatio(m.sharpe_ratio)}</td>
                    <td class="mono ${ddBestWorst}">${formatPct(m.max_drawdown_pct)}</td>
                    <td class="mono cell--negative">${formatPct(m.var_95_pct)}</td>
                    <td class="mono">${betaText}</td>
                    <td class="mono td-52w">
                        <div class="table-range">
                            <span class="table-range__item"><span class="table-range__lbl">L:</span> ${formatPrice(m['52w_low'], m.ticker)}</span>
                            <span class="table-range__sep">–</span>
                            <span class="table-range__item"><span class="table-range__lbl">H:</span> ${formatPrice(m['52w_high'], m.ticker)}</span>
                        </div>
                    </td>
                </tr>
            `;
        });
    }

    function setupTableSorting() {
        const table = document.getElementById('summary-table');
        if (!table) return;

        const headers = table.querySelectorAll('th[data-sort]');
        let sortCol = null;
        let sortDesc = false;

        headers.forEach(th => {
            th.addEventListener('click', () => {
                const col = th.getAttribute('data-sort');

                // Toggle sort direction
                if (sortCol === col) {
                    sortDesc = !sortDesc;
                } else {
                    sortCol = col;
                    sortDesc = true;
                }

                // Update visual arrows on headers
                headers.forEach(h => h.removeAttribute('data-sort-dir'));
                th.setAttribute('data-sort-dir', sortDesc ? 'desc' : 'asc');

                const canonicalMetrics = getCanonicalSummaryMetrics(selectedDateRange);
                const benchmark = canonicalMetrics.find(m => m.ticker === '^NSEI');
                const equities = canonicalMetrics.filter(m => m.ticker !== '^NSEI');

                equities.sort((a, b) => {
                    let valA = a[col];
                    let valB = b[col];
                    if (valA === null || valA === undefined) return 1;
                    if (valB === null || valB === undefined) return -1;

                    if (typeof valA === 'string') {
                        return sortDesc ? valB.localeCompare(valA) : valA.localeCompare(valB);
                    } else {
                        return sortDesc ? valB - valA : valA - valB;
                    }
                });

                const sorted = benchmark ? [benchmark, ...equities] : equities;
                renderTableRows(sorted);
            });
        });
    }

    // -------------------------------------------------------------------------
    // 6. Interactive Slicers, Reset & Event Listeners
    // -------------------------------------------------------------------------
    function setupInstrumentSlicer() {
        const container = document.getElementById('instrument-slicer');
        if (!container) return;

        const btns = container.querySelectorAll('button[data-ticker]');
        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                btns.forEach(b => {
                    b.classList.remove('slicer-btn--active');
                    b.setAttribute('aria-selected', 'false');
                });
                btn.classList.add('slicer-btn--active');
                btn.setAttribute('aria-selected', 'true');
                selectedInstrument = btn.getAttribute('data-ticker');
                updateSelectedInstrumentUI();
            });
        });
    }

    function setupDateSlicer() {
        const container = document.getElementById('date-slicer');
        if (!container) return;

        const btns = container.querySelectorAll('button[data-range]');
        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                const range = btn.getAttribute('data-range');
                applyDateRange(range);
            });
        });
    }

    function setupResetButton() {
        const btn = document.getElementById('btn-reset-filters');
        if (!btn) return;

        btn.addEventListener('click', () => {
            resetFilters();
        });
    }

    function resetFilters() {
        // 1. Reset Instrument to default (RELIANCE.NS)
        selectedInstrument = 'RELIANCE.NS';
        const instBtns = document.querySelectorAll('#instrument-slicer button[data-ticker]');
        instBtns.forEach(b => {
            const isDefault = b.getAttribute('data-ticker') === 'RELIANCE.NS';
            b.classList.toggle('slicer-btn--active', isDefault);
            b.setAttribute('aria-selected', isDefault ? 'true' : 'false');
        });

        // 2. Reset Date Range to 5Y / Full available historical period
        applyDateRange('5Y');

        // 3. Reset Technical Overlays to approved default states (SMA 20 & SMA 50 active, others inactive)
        const overlayContainer = document.getElementById('overlay-toggles');
        if (overlayContainer) {
            const toggles = overlayContainer.querySelectorAll('.toggle-pill');
            toggles.forEach(pill => {
                const overlay = pill.getAttribute('data-overlay');
                const isDefaultActive = (overlay === 'sma_20' || overlay === 'sma_50');
                pill.classList.toggle('toggle-pill--active', isDefaultActive);
                pill.setAttribute('aria-pressed', isDefaultActive ? 'true' : 'false');
            });
        }

        // 4. Reset Active Tab to Executive Overview
        switchTab('tab-overview');

        // 5. Reset Table Sort to original order & clear sort arrows
        const table = document.getElementById('summary-table');
        if (table) {
            table.querySelectorAll('th[data-sort]').forEach(th => th.removeAttribute('data-sort-dir'));
        }
        buildSummaryTable();

        // 6. Update Selected Instrument UI (KPI cards, regime badge, single-stock charts)
        updateSelectedInstrumentUI();
    }

    function setupOverlayToggles() {
        const container = document.getElementById('overlay-toggles');
        if (!container) return;

        const toggles = container.querySelectorAll('.toggle-pill');
        toggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                toggle.classList.toggle('toggle-pill--active');
                const isActive = toggle.classList.contains('toggle-pill--active');
                toggle.setAttribute('aria-pressed', isActive ? 'true' : 'false');
                renderPriceChart();
            });
        });
    }

    // Date boundary calculator: computes exact start and end dates from dataset
    function computeDateRange(rangeType) {
        selectedDateRange = rangeType;
        const benchData = data.instruments_data['^NSEI'];
        if (!benchData) return null;
        const dates = benchData.dates;
        const total = dates.length;
        if (total === 0) return null;

        if (rangeType === '5Y') {
            currentXRange = [dates[0], dates[total - 1]];
            return currentXRange;
        }

        let startIdx = 0;
        const endIdx = total - 1;
        const lastDate = new Date(dates[endIdx]);

        if (rangeType === '1Y') {
            const targetYear = lastDate.getFullYear() - 1;
            const targetStr = `${targetYear}-${String(lastDate.getMonth() + 1).padStart(2, '0')}-${String(lastDate.getDate()).padStart(2, '0')}`;
            startIdx = dates.findIndex(d => d >= targetStr);
            if (startIdx === -1) startIdx = Math.max(0, total - 252);
        } else if (rangeType === '3Y') {
            const targetYear = lastDate.getFullYear() - 3;
            const targetStr = `${targetYear}-${String(lastDate.getMonth() + 1).padStart(2, '0')}-${String(lastDate.getDate()).padStart(2, '0')}`;
            startIdx = dates.findIndex(d => d >= targetStr);
            if (startIdx === -1) startIdx = Math.max(0, total - 756);
        } else if (rangeType === 'YTD') {
            const currentYear = lastDate.getFullYear();
            const targetStr = `${currentYear}-01-01`;
            startIdx = dates.findIndex(d => d >= targetStr);
            if (startIdx === -1) startIdx = 0;
        }

        if (startIdx >= total) startIdx = 0;
        currentXRange = [dates[startIdx], dates[endIdx]];
        return currentXRange;
    }

    // Applies date range to all time series charts (ZERO data recalculation or rebasing)
    function applyDateRange(rangeType) {
        computeDateRange(rangeType);

        // Update active button classes and ARIA attributes
        const container = document.getElementById('date-slicer');
        if (container) {
            const btns = container.querySelectorAll('button[data-range]');
            btns.forEach(b => {
                const isActive = b.getAttribute('data-range') === rangeType;
                b.classList.toggle('date-preset-btn--active', isActive);
                b.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
        }

        // Relayout all time series charts across all tabs
        const update = (rangeType === '5Y')
            ? { 'xaxis.autorange': true }
            : { 'xaxis.range': currentXRange, 'xaxis.autorange': false };

        TIME_SERIES_CHART_IDS.forEach(id => {
            const el = document.getElementById(id);
            if (el && el.data) {
                try {
                    Plotly.relayout(el, update);
                } catch (e) {
                    console.warn(`Error applying date range on ${id}:`, e);
                }
            }
        });

        // Refresh KPI scorecards for the active period
        buildKPICards();

        // Clear sort arrows on summary table and refresh table rows + headers for the active period
        const table = document.getElementById('summary-table');
        if (table) {
            table.querySelectorAll('th[data-sort]').forEach(th => th.removeAttribute('data-sort-dir'));
        }
        buildSummaryTable();
    }

    // Helper: returns the appropriate x-axis configuration for time-series charts
    function getTimeSeriesXAxisConfig(extraConfig = {}) {
        const base = {
            ...LAYOUT_DEFAULTS.xaxis,
            type: 'date',
            ...extraConfig
        };
        if (selectedDateRange !== '5Y' && currentXRange) {
            base.range = [...currentXRange];
            base.autorange = false;
        } else {
            base.autorange = true;
        }
        return base;
    }

    function updateSelectedInstrumentUI() {
        const tickerSpan = document.getElementById('price-chart-ticker');
        if (tickerSpan) {
            tickerSpan.textContent = selectedInstrument;
        }

        const badge = document.getElementById('regime-badge');
        if (badge) {
            const instData = data.instruments_data[selectedInstrument];
            if (instData && instData.bullish_regime && instData.bullish_regime.length > 0) {
                const lastRegime = instData.bullish_regime[instData.bullish_regime.length - 1];
                if (lastRegime === true || lastRegime === 1) {
                    badge.textContent = 'Bullish Regime (SMA-50 > SMA-200)';
                    badge.className = 'badge badge--positive';
                } else {
                    badge.textContent = 'Bearish Regime (SMA-50 ≤ SMA-200)';
                    badge.className = 'badge badge--negative';
                }
            }
        }

        // Re-render KPI cards for the newly selected instrument
        buildKPICards();

        // Render Tab 2 charts (they automatically inherit active date range via getTimeSeriesXAxisConfig)
        renderPriceChart();
        renderRsiChart();
        renderVolumeChart();

        // Render Tab 3 instrument-specific charts
        renderDrawdownChart();
        renderVolatilityChart();
    }

    function renderAllCharts() {
        // Tab 1 visuals
        renderNormalizedChart();
        renderScatterChart();
        render52wChart();

        // Tab 2 visuals
        renderPriceChart();
        renderRsiChart();
        renderVolumeChart();

        // Tab 3 visuals
        renderDrawdownChart();
        renderVolatilityChart();
        renderCorrelationChart();
    }

    // -------------------------------------------------------------------------
    // 7. Chart 1: Normalized Price Performance Comparison (Tab 1 Full Width)
    // -------------------------------------------------------------------------
    function renderNormalizedChart() {
        const traces = data.metadata.instruments.map(ticker => {
            const instData = data.instruments_data[ticker];
            if (!instData || !instData.normalized_price) return null;
            const isBench = ticker === '^NSEI';
            return {
                x: instData.dates,
                y: instData.normalized_price,
                name: ticker,
                mode: 'lines',
                line: {
                    color: COLORS[ticker],
                    dash: isBench ? 'dash' : 'solid',
                    width: isBench ? 2.5 : 1.5
                },
                hovertemplate: `${ticker}: %{y:.2f}<extra></extra>`
            };
        }).filter(Boolean);

        const layout = {
            ...LAYOUT_DEFAULTS,
            xaxis: getTimeSeriesXAxisConfig(),
            yaxis: { ...LAYOUT_DEFAULTS.yaxis, title: 'Normalized Index (Base 100)' }
        };
        Plotly.newPlot('chart-normalized', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 8. Chart 2: Institutional Risk-Return Efficiency Map (Tab 1 Scatter Plot)
    // Fix: Explicit type 'linear' and hovermode 'closest' prevent timestamp interpretation
    // -------------------------------------------------------------------------
    function renderScatterChart() {
        const metrics = data.summary_metrics;
        if (!metrics) return;

        let nseiVol = 13.81;
        const nseiMetric = metrics.find(m => m.ticker === '^NSEI');
        if (nseiMetric && nseiMetric.annualized_volatility_pct) {
            nseiVol = nseiMetric.annualized_volatility_pct;
        }

        // Uniform marker sizes (18px) to prevent perceptual scale distortion
        const traces = metrics.map(m => {
            const isBench = m.ticker === '^NSEI';
            return {
                x: [m.annualized_volatility_pct],
                y: [m.cagr_pct],
                mode: 'markers+text',
                name: m.ticker,
                text: [m.ticker],
                textposition: 'top center',
                textfont: { size: 11, color: '#0f172a', family: '-apple-system, sans-serif' },
                marker: {
                    color: COLORS[m.ticker],
                    size: isBench ? 20 : 18,
                    symbol: isBench ? 'diamond' : 'circle',
                    line: { color: '#ffffff', width: 2 }
                },
                hovertemplate: `<b>${m.ticker}</b> (${DISPLAY_NAMES[m.ticker]})<br>` +
                    `Ann. Volatility: %{x:.2f}%<br>` +
                    `5-Yr CAGR: %{y:.2f}%<br>` +
                    `Sharpe Ratio: ${formatRatio(m.sharpe_ratio)}<br>` +
                    `Beta vs NIFTY: ${isBench ? '1.00 (Benchmark)' : formatRatio(m.beta_nifty)}<extra></extra>`
            };
        });

        const layout = {
            ...LAYOUT_DEFAULTS,
            hovermode: 'closest', // Prevents unified-x timestamp interpretation of numeric values
            xaxis: {
                ...LAYOUT_DEFAULTS.xaxis,
                type: 'linear', // Strictly numeric linear scale
                title: 'Annualized Return Volatility (%)',
                ticksuffix: '%',
                tickformat: '.0f',
                dtick: 5,
                range: [10, 30] // Clean boundary framing 13.8% (NIFTY) to 26% (INFY)
            },
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: '5-Year CAGR (%)',
                ticksuffix: '%',
                tickformat: '.1f',
                dtick: 5,
                range: [-15, 25] // Framing -8.7% (TCS) to +19.3% (SBIN)
            },
            showlegend: false,
            shapes: [
                // 0% Return Horizontal Reference Line
                {
                    type: 'line',
                    xref: 'paper',
                    x0: 0,
                    x1: 1,
                    y0: 0,
                    y1: 0,
                    line: { color: '#94a3b8', width: 1.2, dash: 'solid' }
                },
                // Benchmark Volatility Vertical Reference Line
                {
                    type: 'line',
                    xref: 'x',
                    x0: nseiVol,
                    x1: nseiVol,
                    yref: 'paper',
                    y0: 0,
                    y1: 1,
                    line: { color: '#64748b', width: 1.2, dash: 'dash' }
                }
            ],
            annotations: [
                {
                    xref: 'x',
                    yref: 'paper',
                    x: nseiVol,
                    y: 0.98,
                    xanchor: 'left',
                    yanchor: 'top',
                    text: `NIFTY 50 Vol (${nseiVol.toFixed(1)}%)`,
                    showarrow: false,
                    font: { size: 11.5, color: '#64748b' }
                },
                {
                    xref: 'paper',
                    yref: 'y',
                    x: 0.02,
                    y: 0,
                    xanchor: 'left',
                    yanchor: 'bottom',
                    text: '0% CAGR Breakeven',
                    showarrow: false,
                    font: { size: 11.5, color: '#94a3b8' }
                }
            ]
        };

        Plotly.newPlot('chart-scatter', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 9. Chart 3: 52-Week Range Position Gauge (Tab 1 Horizontal Gauge)
    // -------------------------------------------------------------------------
    function render52wChart() {
        if (!data.summary_metrics || data.summary_metrics.length === 0) return;

        // Canonical Benchmark-First order
        const metrics = getCanonicalSummaryMetrics('5Y');
        const labels = metrics.map(m => m.ticker === '^NSEI' ? 'NIFTY 50' : m.ticker.replace('.NS', ''));
        const tickers = metrics.map(m => m.ticker);

        // Position % = (Last Close - 52W Low) / (52W High - 52W Low) * 100
        const positions = metrics.map(m => {
            const low = m['52w_low'];
            const high = m['52w_high'];
            const close = m.last_close;
            if (low === null || high === null || close === null || isNaN(low) || isNaN(high) || isNaN(close) || high === low) return 0;
            return ((close - low) / (high - low)) * 100;
        });

        const hoverTexts = metrics.map((m, i) => {
            const price = formatPrice(m.last_close, m.ticker);
            const high = formatPrice(m['52w_high'], m.ticker);
            const low = formatPrice(m['52w_low'], m.ticker);
            const pos = positions[i].toFixed(1) + '%';
            return `<b>${m.ticker === '^NSEI' ? 'NIFTY 50 (Benchmark)' : m.ticker}</b><br>` +
                   `Current: ${price}<br>` +
                   `52W Low: ${low}<br>` +
                   `52W High: ${high}<br>` +
                   `Range Position: ${pos}`;
        });

        const traces = [
            // Background 100% full-width corridor track
            {
                type: 'bar',
                x: metrics.map(() => 100),
                y: labels,
                orientation: 'h',
                name: '52W Corridor',
                marker: { color: '#f1f5f9' },
                hoverinfo: 'none',
                showlegend: false
            },
            // Current position progress bar
            {
                type: 'bar',
                x: positions,
                y: labels,
                orientation: 'h',
                name: 'Position in 52W Corridor',
                marker: { color: tickers.map(t => COLORS[t]) },
                text: positions.map(p => p.toFixed(1) + '%'),
                textposition: 'outside',
                textfont: { size: 11, color: '#334155' },
                cliponaxis: false,
                hovertext: hoverTexts,
                hoverinfo: 'text',
                showlegend: false
            }
        ];

        const layout = {
            ...LAYOUT_DEFAULTS,
            barmode: 'overlay',
            hovermode: 'closest',
            xaxis: {
                ...LAYOUT_DEFAULTS.xaxis,
                type: 'linear',
                title: 'Position Within 52-Week Range (%)',
                range: [0, 105],
                ticksuffix: '%',
                tickvals: [0, 25, 50, 75, 100]
            },
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'category',
                autorange: 'reversed',
                tickfont: { size: 12, color: '#1e293b' }
            },
            margin: { t: 25, r: 40, b: 40, l: 80 }
        };

        Plotly.newPlot('chart-52w', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 10. Chart 4: Primary Price Action & Trend Channel (Tab 2 Candlestick + Overlays)
    // -------------------------------------------------------------------------
    function renderPriceChart() {
        const instData = data.instruments_data[selectedInstrument];
        if (!instData) return;

        const traces = [];

        // Primary Candlestick
        traces.push({
            x: instData.dates,
            open: instData.adj_open,
            high: instData.adj_high,
            low: instData.adj_low,
            close: instData.adj_close,
            type: 'candlestick',
            name: selectedInstrument,
            increasing: { line: { color: '#10b981', width: 1 }, fillcolor: '#10b981' },
            decreasing: { line: { color: '#ef4444', width: 1 }, fillcolor: '#ef4444' }
        });

        // Overlay Moving Averages and Bollinger Bands based on toggles
        const togglesContainer = document.getElementById('overlay-toggles');
        if (togglesContainer) {
            const activeToggles = Array.from(togglesContainer.querySelectorAll('.toggle-pill--active'))
                .map(t => t.getAttribute('data-overlay'));

            const overlayConfig = {
                'sma_20':  { color: '#2563eb', name: 'SMA 20', width: 1.5 },
                'sma_50':  { color: '#d97706', name: 'SMA 50', width: 1.5 },
                'sma_200': { color: '#7c3aed', name: 'SMA 200', width: 1.8 },
                'ema_20':  { color: '#ec4899', name: 'EMA 20', width: 1.5 }
            };

            // Moving Averages
            activeToggles.forEach(overlay => {
                if (instData[overlay] && overlay !== 'bb') {
                    traces.push({
                        x: instData.dates,
                        y: instData[overlay],
                        type: 'scatter',
                        mode: 'lines',
                        name: overlayConfig[overlay].name,
                        line: { color: overlayConfig[overlay].color, width: overlayConfig[overlay].width },
                        hoverinfo: 'name+y'
                    });
                }
            });

            // Bollinger Bands Toggle on Price Chart
            if (activeToggles.includes('bb') && instData.bb_upper && instData.bb_lower) {
                traces.push({
                    x: instData.dates,
                    y: instData.bb_upper,
                    mode: 'lines',
                    line: { color: 'rgba(59, 130, 246, 0.4)', width: 1, dash: 'dot' },
                    name: 'BB Upper (+2σ)',
                    hoverinfo: 'name+y'
                });
                traces.push({
                    x: instData.dates,
                    y: instData.bb_middle,
                    mode: 'lines',
                    line: { color: 'rgba(59, 130, 246, 0.6)', width: 1, dash: 'dash' },
                    name: 'BB Middle (20d)',
                    hoverinfo: 'name+y'
                });
                traces.push({
                    x: instData.dates,
                    y: instData.bb_lower,
                    mode: 'lines',
                    line: { color: 'rgba(59, 130, 246, 0.4)', width: 1, dash: 'dot' },
                    name: 'BB Lower (-2σ)',
                    hoverinfo: 'name+y'
                });
            }
        }

        // Discrete Crossover Impulse Markers
        if (instData.golden_cross_event) {
            const gcX = [];
            const gcY = [];
            instData.golden_cross_event.forEach((v, i) => {
                if (v === 1 || v === true) {
                    gcX.push(instData.dates[i]);
                    gcY.push(instData.adj_close[i]);
                }
            });
            if (gcX.length > 0) {
                traces.push({
                    x: gcX,
                    y: gcY,
                    mode: 'markers',
                    name: 'Golden Cross (SMA 50 > 200)',
                    marker: { symbol: 'triangle-up', color: '#10b981', size: 13, line: { color: '#065f46', width: 1 } },
                    hoverinfo: 'name+x+y'
                });
            }
        }

        if (instData.death_cross_event) {
            const dcX = [];
            const dcY = [];
            instData.death_cross_event.forEach((v, i) => {
                if (v === 1 || v === true) {
                    dcX.push(instData.dates[i]);
                    dcY.push(instData.adj_close[i]);
                }
            });
            if (dcX.length > 0) {
                traces.push({
                    x: dcX,
                    y: dcY,
                    mode: 'markers',
                    name: 'Death Cross (SMA 50 < 200)',
                    marker: { symbol: 'triangle-down', color: '#ef4444', size: 13, line: { color: '#991b1b', width: 1 } },
                    hoverinfo: 'name+x+y'
                });
            }
        }

        const yAxisTitle = selectedInstrument === '^NSEI' ? 'Index Points' : 'Adjusted Price (₹)';
        const layout = {
            ...LAYOUT_DEFAULTS,
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: yAxisTitle,
                tickformat: ',.0f'
            },
            xaxis: getTimeSeriesXAxisConfig({
                rangeslider: { visible: true, thickness: 0.06 }
            }),
            showlegend: true
        };

        Plotly.newPlot('chart-price', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 11. Chart 5: Wilder's RSI-14 Momentum Oscillator (Tab 2 Oscillator)
    // -------------------------------------------------------------------------
    function renderRsiChart() {
        const instData = data.instruments_data[selectedInstrument];
        if (!instData || !instData.rsi_14) return;

        const traces = [{
            x: instData.dates,
            y: instData.rsi_14,
            mode: 'lines',
            name: 'RSI-14',
            line: { color: '#7c3aed', width: 1.5 },
            hovertemplate: 'RSI-14: %{y:.2f}<extra></extra>'
        }];

        const layout = {
            ...LAYOUT_DEFAULTS,
            xaxis: getTimeSeriesXAxisConfig(),
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: 'RSI Level',
                range: [0, 100],
                fixedrange: true,
                tickvals: [0, 30, 50, 70, 100],
                tickformat: '.0f'
            },
            shapes: [
                // Overbought shaded area (70 - 100)
                { type: 'rect', xref: 'paper', x0: 0, x1: 1, y0: 70, y1: 100, fillcolor: 'rgba(239, 68, 68, 0.08)', line: { width: 0 }, layer: 'below' },
                // Oversold shaded area (0 - 30)
                { type: 'rect', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 30, fillcolor: 'rgba(16, 185, 129, 0.08)', line: { width: 0 }, layer: 'below' },
                // 70 reference line
                { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 70, y1: 70, line: { color: 'rgba(239, 68, 68, 0.6)', width: 1, dash: 'dash' } },
                // 30 reference line
                { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 30, y1: 30, line: { color: 'rgba(16, 185, 129, 0.6)', width: 1, dash: 'dash' } },
                // 50 neutral midline
                { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 50, y1: 50, line: { color: 'rgba(148, 163, 184, 0.4)', width: 0.8, dash: 'dot' } }
            ]
        };
        Plotly.newPlot('chart-rsi', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 12. Chart 6: Trading Volume & 20-Day SMA Monitor (Tab 2 Volume)
    // -------------------------------------------------------------------------
    function renderVolumeChart() {
        const instData = data.instruments_data[selectedInstrument];
        if (!instData || !instData.volume) return;

        const isBench = selectedInstrument === '^NSEI';
        const yTitle = isBench ? 'Index Traded Volume' : 'Traded Volume (Shares)';

        // Color bars: amber for spike ratio > 2.0, neutral slate otherwise
        const barColors = instData.volume_spike_ratio
            ? instData.volume_spike_ratio.map(r => (r !== null && r > 2.0) ? '#d97706' : 'rgba(100, 116, 139, 0.45)')
            : 'rgba(100, 116, 139, 0.45)';

        const traces = [{
            x: instData.dates,
            y: instData.volume,
            type: 'bar',
            name: 'Volume',
            marker: { color: barColors },
            hovertemplate: 'Volume: %{y:,}<extra></extra>'
        }];

        if (instData.volume_sma_20) {
            traces.push({
                x: instData.dates,
                y: instData.volume_sma_20,
                type: 'scatter',
                mode: 'lines',
                name: 'Volume SMA 20',
                line: { color: '#1e293b', width: 1.5 },
                hovertemplate: '20d SMA: %{y:,}<extra></extra>'
            });
        }

        const layout = {
            ...LAYOUT_DEFAULTS,
            xaxis: getTimeSeriesXAxisConfig(),
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: yTitle,
                rangemode: 'tozero',
                tickformat: '~s'
            },
            bargap: 0.15
        };
        Plotly.newPlot('chart-volume', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 13. Chart 7: Underwater Drawdown Profile (Tab 3 Area Chart)
    // -------------------------------------------------------------------------
    function renderDrawdownChart() {
        const instData = data.instruments_data[selectedInstrument];
        if (!instData || !instData.drawdown) return;

        const traces = [{
            x: instData.dates,
            y: instData.drawdown.map(v => (v !== null ? v * 100 : null)),
            mode: 'lines',
            fill: 'tozeroy',
            name: `${selectedInstrument} Drawdown`,
            line: { color: '#ef4444', width: 1 },
            fillcolor: 'rgba(239, 68, 68, 0.18)',
            hovertemplate: 'Drawdown: %{y:.2f}%<extra></extra>'
        }];

        const layout = {
            ...LAYOUT_DEFAULTS,
            xaxis: getTimeSeriesXAxisConfig(),
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: 'Drawdown (%)',
                ticksuffix: '%',
                tickformat: '.0f'
            }
        };
        Plotly.newPlot('chart-drawdown', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 14. Chart 8: Rolling 30-Day Annualized Volatility Regime (Tab 3 Regime)
    // -------------------------------------------------------------------------
    function renderVolatilityChart() {
        const instData = data.instruments_data[selectedInstrument];
        const benchData = data.instruments_data['^NSEI'];
        if (!instData || !instData.rolling_vol_30d) return;

        const traces = [{
            x: instData.dates,
            y: instData.rolling_vol_30d.map(v => (v !== null ? v * 100 : null)),
            mode: 'lines',
            name: selectedInstrument,
            line: { color: COLORS[selectedInstrument], width: 1.5 },
            hovertemplate: `${selectedInstrument}: %{y:.2f}%<extra></extra>`
        }];

        if (selectedInstrument !== '^NSEI' && benchData && benchData.rolling_vol_30d) {
            traces.push({
                x: benchData.dates,
                y: benchData.rolling_vol_30d.map(v => (v !== null ? v * 100 : null)),
                mode: 'lines',
                name: '^NSEI (Benchmark)',
                line: { color: COLORS['^NSEI'], width: 1.5, dash: 'dash' },
                hovertemplate: `^NSEI: %{y:.2f}%<extra></extra>`
            });
        }

        const layout = {
            ...LAYOUT_DEFAULTS,
            xaxis: getTimeSeriesXAxisConfig(),
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'linear',
                title: '30-Day Volatility (%)',
                ticksuffix: '%',
                tickformat: '.0f'
            }
        };
        Plotly.newPlot('chart-volatility', traces, layout, PLOTLY_CONFIG);
    }

    // -------------------------------------------------------------------------
    // 15. Chart 9: Cross-Asset Pearson Correlation Heatmap (Tab 3 Matrix)
    // -------------------------------------------------------------------------
    function renderCorrelationChart() {
        const corrData = data.correlation_matrix;
        if (!corrData) return;

        const symbols = corrData.symbols;
        const matrix = corrData.matrix;

        // Clean display labels without '.NS' extension for readability
        const cleanLabels = symbols.map(s => s === '^NSEI' ? 'NIFTY 50' : s.replace('.NS', ''));
        const revCleanLabels = [...cleanLabels].reverse();
        const revMatrix = [...matrix].reverse();

        const traces = [{
            x: cleanLabels,
            y: revCleanLabels,
            z: revMatrix,
            type: 'heatmap',
            colorscale: [
                [0.0, '#3b82f6'], // Cool blue for low/negative correlation
                [0.5, '#f8fafc'], // Neutral white at midpoint
                [1.0, '#dc2626']  // Warm red for high positive correlation
            ],
            zmin: -0.2,
            zmax: 1.0,
            showscale: true,
            colorbar: {
                title: 'Pearson r',
                titleside: 'right',
                thickness: 12,
                len: 0.8
            },
            text: revMatrix.map(row => row.map(val => (val !== null ? val.toFixed(2) : '-'))),
            texttemplate: '%{text}',
            textfont: { size: 11.5, color: '#0f172a' },
            hovertemplate: '%{x} vs %{y}: r = %{z:.4f}<extra></extra>'
        }];

        const layout = {
            ...LAYOUT_DEFAULTS,
            margin: { t: 30, r: 40, b: 50, l: 85 },
            xaxis: {
                ...LAYOUT_DEFAULTS.xaxis,
                type: 'category',
                tickangle: 0,
                tickfont: { size: 11.5, color: '#0f172a' }
            },
            yaxis: {
                ...LAYOUT_DEFAULTS.yaxis,
                type: 'category',
                tickfont: { size: 11.5, color: '#0f172a' }
            }
        };

        Plotly.newPlot('chart-correlation', traces, layout, PLOTLY_CONFIG);
    }

    // Run Initialization
    init();
});
