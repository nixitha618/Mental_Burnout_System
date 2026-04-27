// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// User Management
let currentUserId = localStorage.getItem('burnout_user_id');
let riskChart, importanceChart, trendChart;

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    // Initialize user
    initUser();
    
    // Initialize form
    const form = document.getElementById('burnoutForm');
    const resetBtn = document.getElementById('resetBtn');
    
    // Initialize range input displays
    initRangeInputs();
    
    // Form submission
    form.addEventListener('submit', handleFormSubmit);
    
    // Reset button
    resetBtn.addEventListener('click', resetForm);
    
    // Guidance buttons
    initGuidanceButtons();
    
    // Enter key for guidance input
    document.getElementById('guidanceQuery').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleGuidanceQuery();
        }
    });
    
    // Ask guidance button
    document.getElementById('askGuidanceBtn').addEventListener('click', handleGuidanceQuery);
    
    // Check API health on load
    checkAPIHealth();
    
    // Load sample historical data
    loadHistoricalData();
    
    // Initialize subscription form
    initSubscriptionForm();
});

// Initialize or get user ID
async function initUser() {
    if (!currentUserId) {
        try {
            const response = await fetch(`${API_BASE_URL}/user/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            currentUserId = data.user_id;
            localStorage.setItem('burnout_user_id', currentUserId);
            console.log('✅ New user created:', currentUserId);
            showNotification('Welcome! Your assessments will be saved.', 'success');
            
            // Show email section after user creation
            checkAndShowEmailSection();
        } catch (error) {
            console.error('Failed to create user:', error);
            currentUserId = `LOCAL_${Date.now()}`;
            localStorage.setItem('burnout_user_id', currentUserId);
            showNotification('Offline Mode - Data not saved to server', 'warning');
        }
    } else {
        console.log('✅ Existing user:', currentUserId);
        await loadUserHistory(currentUserId);
        checkAndShowEmailSection();
    }
    return currentUserId;
}

// Check if API is running
async function checkAPIHealth() {
    try {
        console.log('🔍 Checking API health...');
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ API is healthy:', data);
            showNotification('Connected to AI Backend!', 'success');
        } else {
            console.warn('⚠️ API health check failed');
            showNotification('Using Demo Mode - Backend not connected', 'warning');
        }
    } catch (error) {
        console.warn('⚠️ API not reachable. Using demo mode.');
        showNotification('Demo Mode - Backend API not running', 'warning');
    }
}

// Show notification
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#f59e0b'};
        color: white;
        border-radius: 8px;
        z-index: 9999;
        animation: slideIn 0.3s ease;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Initialize range input displays
function initRangeInputs() {
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    rangeInputs.forEach(input => {
        const valueDisplay = document.getElementById(input.id + '_value') || 
                            document.getElementById(input.id.replace('_level', '_value'));
        if (valueDisplay) {
            valueDisplay.textContent = input.value;
            input.addEventListener('input', function() {
                valueDisplay.textContent = this.value;
            });
        }
    });
}

// Handle form submission
async function handleFormSubmit(e) {
    e.preventDefault();
    
    document.getElementById('loadingOverlay').style.display = 'flex';
    const userId = await initUser();
    
    const formData = {
        sleep_hours: parseFloat(document.getElementById('sleep_hours').value),
        workload_hours: parseFloat(document.getElementById('workload_hours').value),
        stress_level: parseInt(document.getElementById('stress_level').value),
        screen_time: parseFloat(document.getElementById('screen_time').value),
        physical_activity: parseInt(document.getElementById('physical_activity').value),
        social_interaction: parseFloat(document.getElementById('social_interaction').value),
        meal_quality: parseInt(document.getElementById('meal_quality').value),
        productivity_score: parseInt(document.getElementById('productivity_score').value)
    };
    
    try {
        console.log('📤 Sending prediction request:', formData);
        
        const prediction = await predictBurnoutRisk(formData);
        console.log('📥 Prediction response:', prediction);
        
        const explanation = await getExplanation(formData);
        console.log('📥 Explanation response:', explanation);
        
        await saveAssessment(formData, prediction);
        updateResults(prediction, explanation, formData);
        await loadUserHistory(userId);
        
        document.querySelector('.results-section').style.display = 'block';
        document.querySelector('.results-section').scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('❌ Error:', error);
        alert('An error occurred while analyzing your data. Please try again.');
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// REAL API CALL: Predict burnout risk
async function predictBurnoutRisk(data) {
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Prediction API error:', error);
        return fallbackPredictBurnoutRisk(data);
    }
}

// REAL API CALL: Get explanation for prediction
async function getExplanation(data) {
    try {
        const response = await fetch(`${API_BASE_URL}/explain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Explanation API error:', error);
        return fallbackGenerateExplanation(data);
    }
}

// Save assessment to database and trigger alerts
async function saveAssessment(inputData, prediction) {
    try {
        const userId = localStorage.getItem('burnout_user_id');
        if (!userId || userId.startsWith('LOCAL_')) {
            console.log('Skipping save - offline mode');
            return;
        }
        
        await fetch(`${API_BASE_URL}/assessment/save?user_id=${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input_data: inputData, prediction: prediction })
        });
        console.log('✅ Assessment saved to database');
        
        // Send high risk alert if needed
        if (prediction.risk_level === 'High' && prediction.risk_score >= 60) {
            await fetch(`${API_BASE_URL}/send/alert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    assessment_data: inputData,
                    prediction: prediction
                })
            });
            console.log('📧 High risk alert triggered');
            showNotification('High risk detected! An alert has been sent to your email.', 'warning');
        }
        
    } catch (error) {
        console.error('Failed to save assessment:', error);
    }
}

// Load user history
async function loadUserHistory(userId) {
    try {
        if (userId.startsWith('LOCAL_')) return;
        
        const response = await fetch(`${API_BASE_URL}/history/${userId}?limit=10`);
        if (response.ok) {
            const data = await response.json();
            console.log('📊 User history:', data);
            updateHistoryDisplay(data);
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// Update history display in UI
function updateHistoryDisplay(historyData) {
    let historySection = document.getElementById('historySection');
    if (!historySection) {
        historySection = document.createElement('div');
        historySection.id = 'historySection';
        historySection.className = 'history-card';
        historySection.innerHTML = `
            <h3><i class="fas fa-chart-line"></i> Your Assessment History</h3>
            <div id="statsDisplay" class="stats-display"></div>
            <div id="historyList" class="history-list"></div>
        `;
        const guidanceCard = document.querySelector('.guidance-card');
        if (guidanceCard) {
            guidanceCard.insertAdjacentElement('afterend', historySection);
        }
    }
    
    const stats = historyData.statistics || {};
    const statsHtml = `
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">${stats.total_assessments || 0}</div><div class="stat-label">Total</div></div>
            <div class="stat-card"><div class="stat-value">${stats.average_risk_score || 0}%</div><div class="stat-label">Avg Risk</div></div>
            <div class="stat-card"><div class="stat-value" style="color:#10b981">${stats.risk_level_counts?.Low || 0}</div><div class="stat-label">Low</div></div>
            <div class="stat-card"><div class="stat-value" style="color:#f59e0b">${stats.risk_level_counts?.Medium || 0}</div><div class="stat-label">Medium</div></div>
            <div class="stat-card"><div class="stat-value" style="color:#ef4444">${stats.risk_level_counts?.High || 0}</div><div class="stat-label">High</div></div>
        </div>
    `;
    
    const statsDisplay = document.getElementById('statsDisplay');
    if (statsDisplay) statsDisplay.innerHTML = statsHtml;
    
    const history = historyData.history || [];
    const historyList = document.getElementById('historyList');
    if (historyList) {
        if (history.length > 0) {
            historyList.innerHTML = `
                <h4 style="margin: 1rem 0 0.5rem 0;">Recent Assessments</h4>
                <div class="history-timeline">
                    ${history.slice(0, 10).map(record => `
                        <div class="history-item ${record.risk_level.toLowerCase()}">
                            <div class="history-date">${new Date(record.date).toLocaleDateString()}</div>
                            <div class="history-risk">${record.risk_level}</div>
                            <div class="history-score">${Math.round(record.risk_score)}%</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            historyList.innerHTML = '<p style="text-align:center; color:#6b7280; padding:1rem;">No assessments yet.</p>';
        }
    }
}

// FALLBACK: Calculate risk score (demo mode)
function fallbackCalculateRiskScore(data) {
    const sleepScore = Math.max(0, Math.min(100, ((8 - data.sleep_hours) / 8) * 100));
    const stressScore = (data.stress_level / 10) * 100;
    const screenScore = Math.min(100, (data.screen_time / 12) * 100);
    const workloadScore = Math.min(100, (data.workload_hours / 12) * 100);
    const activityScore = Math.max(0, 100 - (data.physical_activity / 60) * 100);
    const socialScore = Math.max(0, 100 - (data.social_interaction / 8) * 100);
    const mealScore = 100 - (data.meal_quality / 10) * 100;
    const productivityScore = 100 - (data.productivity_score / 10) * 100;
    
    const totalScore = (
        sleepScore * 0.15 + stressScore * 0.2 + screenScore * 0.1 +
        workloadScore * 0.15 + activityScore * 0.1 + socialScore * 0.1 +
        mealScore * 0.1 + productivityScore * 0.1
    );
    
    let level;
    if (totalScore < 30) level = 'Low';
    else if (totalScore < 60) level = 'Medium';
    else level = 'High';
    
    return { score: totalScore, level };
}

// FALLBACK: Predict burnout risk (demo mode)
async function fallbackPredictBurnoutRisk(data) {
    return new Promise(resolve => {
        setTimeout(() => {
            const riskScore = fallbackCalculateRiskScore(data);
            resolve({
                risk_level: riskScore.level,
                risk_score: riskScore.score,
                confidence: 0.85 + Math.random() * 0.1,
                all_probabilities: {
                    'Low': riskScore.level === 'Low' ? riskScore.score/100 : Math.random() * 0.3,
                    'Medium': riskScore.level === 'Medium' ? riskScore.score/100 : Math.random() * 0.3,
                    'High': riskScore.level === 'High' ? riskScore.score/100 : Math.random() * 0.3
                }
            });
        }, 1500);
    });
}

// FALLBACK: Generate explanation (demo mode)
function fallbackGenerateExplanation(data) {
    const factors = [];
    const importance = {};
    
    if (data.sleep_hours < 6) {
        factors.push({ factor: 'sleep_hours', impact: 'high', message: 'Insufficient sleep significantly increases burnout risk' });
        importance.sleep_hours = 0.25;
    } else if (data.sleep_hours > 9) {
        factors.push({ factor: 'sleep_hours', impact: 'medium', message: 'Excessive sleep may indicate fatigue or recovery needs' });
        importance.sleep_hours = 0.15;
    } else {
        importance.sleep_hours = 0.1;
    }
    
    if (data.stress_level > 7) {
        factors.push({ factor: 'stress_level', impact: 'high', message: 'High stress levels are a primary burnout indicator' });
        importance.stress_level = 0.3;
    } else {
        importance.stress_level = 0.15;
    }
    
    if (data.workload_hours > 10) {
        factors.push({ factor: 'workload_hours', impact: 'high', message: 'Excessive workload hours increase burnout risk' });
        importance.workload_hours = 0.2;
    } else {
        importance.workload_hours = 0.12;
    }
    
    if (data.physical_activity < 20) {
        factors.push({ factor: 'physical_activity', impact: 'medium', message: 'Low physical activity may contribute to burnout' });
        importance.physical_activity = 0.15;
    } else {
        importance.physical_activity = 0.08;
    }
    
    if (data.social_interaction < 1) {
        factors.push({ factor: 'social_interaction', impact: 'medium', message: 'Limited social interaction can increase isolation' });
        importance.social_interaction = 0.12;
    } else {
        importance.social_interaction = 0.07;
    }
    
    if (data.meal_quality < 5) {
        factors.push({ factor: 'meal_quality', impact: 'medium', message: 'Poor nutrition affects mental resilience' });
        importance.meal_quality = 0.1;
    } else {
        importance.meal_quality = 0.06;
    }
    
    if (data.productivity_score < 4) {
        factors.push({ factor: 'productivity_score', impact: 'medium', message: 'Low productivity may indicate burnout symptoms' });
        importance.productivity_score = 0.12;
    } else {
        importance.productivity_score = 0.07;
    }
    
    return {
        factors: factors,
        importance: importance,
        summary: factors.length > 0 ? 
            `Key factors: ${factors.map(f => f.factor.replace('_', ' ')).join(', ')}` :
            'Your metrics are within healthy ranges!'
    };
}

// Update UI with results
function updateResults(prediction, explanation, formData) {
    console.log('Updating UI with:', { prediction, explanation });
    
    const riskLevel = document.getElementById('riskLevel');
    const riskProgress = document.getElementById('riskProgress');
    const riskDescription = document.getElementById('riskDescription');
    
    const level = prediction.risk_level;
    riskLevel.textContent = level;
    riskLevel.style.color = level === 'High' ? '#ef4444' : level === 'Medium' ? '#f59e0b' : '#10b981';
    
    const riskScore = prediction.risk_score || (level === 'Low' ? 25 : level === 'Medium' ? 60 : 85);
    riskProgress.style.width = riskScore + '%';
    
    const descriptions = {
        'Low': '🌟 Your burnout risk is currently low. Keep maintaining healthy habits!',
        'Medium': '⚠️ You show moderate signs of burnout risk. Consider stress management techniques.',
        'High': '🚨 Your burnout risk is high! Take immediate action and prioritize self-care.'
    };
    riskDescription.textContent = descriptions[level] || '';
    
    // Display probability distribution chart
    if (prediction.all_probabilities) {
        updateProbabilityChart(prediction.all_probabilities);
    }
    
    // Update insights
    if (explanation.concerning_factors) {
        updateInsightsFromAPI(explanation, formData);
        updateImportanceChart(explanation.global_feature_importance || explanation.importance);
    } else {
        updateInsights(explanation, formData);
        updateImportanceChart(explanation.importance);
    }
    
    updateMetricsChart(formData);
    updateTrendChart(level);
}

// Update probability chart
function updateProbabilityChart(probabilities) {
    let probCanvas = document.getElementById('probabilityChart');
    
    if (!probCanvas) {
        const chartCard = document.querySelector('.chart-card:last-child');
        const newCard = document.createElement('div');
        newCard.className = 'chart-card';
        newCard.innerHTML = `
            <h3><i class="fas fa-chart-pie"></i> Risk Probability Distribution</h3>
            <div class="chart-container">
                <canvas id="probabilityChart"></canvas>
            </div>
        `;
        const chartsGrid = document.querySelector('.charts-grid');
        if (chartsGrid) {
            chartsGrid.appendChild(newCard);
        }
        probCanvas = document.getElementById('probabilityChart');
    }
    
    if (probCanvas) {
        const ctx = probCanvas.getContext('2d');
        
        if (window.probChart) {
            window.probChart.destroy();
        }
        
        window.probChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                datasets: [{
                    data: [
                        (probabilities.Low * 100).toFixed(1),
                        (probabilities.Medium * 100).toFixed(1),
                        (probabilities.High * 100).toFixed(1)
                    ],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { size: 12, weight: '600' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw}%`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }
}

// Update insights from API response
function updateInsightsFromAPI(explanation, formData) {
    const insightsContent = document.getElementById('insightsContent');
    
    let html = `<p><strong>${explanation.explanation || 'AI Analysis:'}</strong></p>`;
    
    if (explanation.concerning_factors && explanation.concerning_factors.length > 0) {
        html += '<h4>⚠️ Concerning Factors:</h4><ul>';
        explanation.concerning_factors.forEach(factor => {
            html += `<li><strong>${factor.feature.replace('_', ' ')}:</strong> ${factor.issue}<br>💡 ${factor.recommendation}</li>`;
        });
        html += '</ul>';
    }
    
    if (explanation.recommendations && explanation.recommendations.length > 0) {
        html += '<h4>📋 Recommendations:</h4><ul>';
        explanation.recommendations.forEach(rec => {
            html += `<li>✓ ${rec}</li>`;
        });
        html += '</ul>';
    }
    
    html += '<div style="margin-top:1rem; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); color:white; border-radius:1rem;">';
    html += '<strong>💡 Tips:</strong><br>';
    if (formData.sleep_hours < 7) html += '• Aim for 7-9 hours of sleep<br>';
    if (formData.stress_level > 7) html += '• Practice deep breathing or meditation<br>';
    if (formData.physical_activity < 30) html += '• Try 30 minutes of daily activity<br>';
    if (formData.social_interaction < 2) html += '• Schedule time for social connections<br>';
    html += '</div>';
    
    insightsContent.innerHTML = html;
}

// Update insights content (fallback)
function updateInsights(explanation, formData) {
    const insightsContent = document.getElementById('insightsContent');
    
    let html = `<p><strong>${explanation.summary}</strong></p>`;
    
    if (explanation.factors && explanation.factors.length > 0) {
        html += '<ul>';
        explanation.factors.forEach(factor => {
            html += `<li>${factor.impact === 'high' ? '🔴' : '🟡'} <strong>${factor.factor.replace('_', ' ')}:</strong> ${factor.message}</li>`;
        });
        html += '</ul>';
    }
    
    html += '<div style="margin-top:1rem; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); color:white; border-radius:1rem;">';
    html += '<strong>💡 Tips:</strong><br>';
    if (formData.sleep_hours < 7) html += '• Aim for 7-9 hours of sleep<br>';
    if (formData.stress_level > 7) html += '• Practice deep breathing or meditation<br>';
    if (formData.physical_activity < 30) html += '• Try 30 minutes of daily activity<br>';
    html += '</div>';
    
    insightsContent.innerHTML = html;
}

// Helper function to create gradients
function createGradient(ctx, color1, color2) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);
    return gradient;
}

// Update metrics chart
function updateMetricsChart(data) {
    const ctx = document.getElementById('metricsChart')?.getContext('2d');
    if (!ctx) return;
    
    if (riskChart) riskChart.destroy();
    
    const gradients = [
        createGradient(ctx, '#4f46e5', '#818cf8'),
        createGradient(ctx, '#f59e0b', '#fbbf24'),
        createGradient(ctx, '#ef4444', '#f87171'),
        createGradient(ctx, '#10b981', '#34d399'),
        createGradient(ctx, '#8b5cf6', '#a78bfa'),
        createGradient(ctx, '#ec4899', '#f472b6'),
        createGradient(ctx, '#f59e0b', '#fbbf24'),
        createGradient(ctx, '#4f46e5', '#818cf8')
    ];
    
    riskChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Sleep', 'Workload', 'Stress', 'Screen', 'Activity', 'Social', 'Meals', 'Productivity'],
            datasets: [{
                label: 'Your Metrics',
                data: [
                    data.sleep_hours, data.workload_hours, data.stress_level, data.screen_time,
                    Math.round(data.physical_activity / 10), data.social_interaction, data.meal_quality, data.productivity_score
                ],
                backgroundColor: gradients,
                borderRadius: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, max: 12 } }
        }
    });
}

// Update importance chart
function updateImportanceChart(importance) {
    const ctx = document.getElementById('importanceChart')?.getContext('2d');
    if (!ctx) return;
    
    if (importanceChart) importanceChart.destroy();
    
    if (!importance || Object.keys(importance).length === 0) {
        importance = { 'sleep_hours': 0.2, 'stress_level': 0.3, 'workload_hours': 0.2 };
    }
    
    const sorted = Object.entries(importance).sort((a,b) => b[1] - a[1]).slice(0, 5);
    
    importanceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: sorted.map(i => i[0].replace('_', ' ')),
            datasets: [{
                data: sorted.map(i => (i[1] * 100).toFixed(1)),
                backgroundColor: ['#4f46e5', '#f59e0b', '#ef4444', '#10b981', '#8b5cf6'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'bottom', labels: { font: { size: 11 } } }
            }
        }
    });
}

// Update trend chart
function updateTrendChart(currentRisk) {
    const ctx = document.getElementById('trendChart')?.getContext('2d');
    if (!ctx) return;
    
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Today'];
    const riskValues = generateTrendData(currentRisk);
    
    if (trendChart) trendChart.destroy();
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: days,
            datasets: [{
                label: 'Burnout Risk Trend',
                data: riskValues,
                borderColor: '#4f46e5',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                pointBackgroundColor: riskValues.map(v => v < 30 ? '#10b981' : v < 60 ? '#f59e0b' : '#ef4444'),
                pointBorderColor: 'white',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            let risk = value >= 60 ? 'High Risk' : value >= 30 ? 'Medium Risk' : 'Low Risk';
                            return `Risk Score: ${value.toFixed(1)}% (${risk})`;
                        }
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: true, 
                    max: 100, 
                    title: { display: true, text: 'Risk Score (%)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: { grid: { display: false } }
            }
        }
    });
}

// Generate trend data
function generateTrendData(currentRisk) {
    let baseValue;
    switch(currentRisk) {
        case 'Low': baseValue = 25; break;
        case 'Medium': baseValue = 55; break;
        case 'High': baseValue = 80; break;
        default: baseValue = 50;
    }
    return [
        baseValue - 15, baseValue - 10, baseValue - 5, baseValue, baseValue + 3, baseValue + 5, baseValue + 2
    ].map(v => Math.min(100, Math.max(0, v)));
}

// REAL API CALL: Get guidance
async function getGuidance(query, context = {}) {
    const response = await fetch(`${API_BASE_URL}/guidance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, context: context })
    });
    return await response.json();
}

// Initialize guidance buttons
function initGuidanceButtons() {
    document.querySelectorAll('.guidance-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.getElementById('guidanceQuery').value = this.getAttribute('data-query');
            handleGuidanceQuery();
        });
    });
}

// =====================================================
// ✅ UPDATED: Handle guidance query with Groq debug logs
// =====================================================
async function handleGuidanceQuery() {
    const query = document.getElementById('guidanceQuery').value.trim();
    if (!query) {
        alert('Please enter a question.');
        return;
    }

    const responseContent = document.getElementById('responseContent');
    responseContent.innerHTML = '<div style="text-align:center;"><i class="fas fa-spinner fa-spin"></i> Thinking...</div>';

    // Show a badge in the UI while loading
    showGenerationBadge('loading', '⏳ Waiting for Groq...');

    try {
        const context = {
            sleep_hours: document.getElementById('sleep_hours')?.value,
            stress_level: document.getElementById('stress_level')?.value,
            risk_level: document.getElementById('riskLevel')?.textContent
        };

        console.log('📤 Sending guidance request to backend...');
        console.log('❓ Query:', query);
        console.log('🧠 Context sent:', context);

        const startTime = performance.now();
        const guidance = await getGuidance(query, context);
        const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

        // ─── Groq debug logs ───────────────────────────────
        console.log('%c📥 GROQ GUIDANCE RESPONSE', 'color: #10b981; font-weight: bold; font-size: 14px;');
        console.log('🔧 Generation Method :', guidance.generation_method);
        console.log('💬 Guidance Text     :', guidance.guidance || guidance.response);
        console.log('📚 Sources Used      :', guidance.sources);
        console.log('🧩 Context Used      :', guidance.context_used);
        console.log(`⏱️ Response Time     : ${elapsed}s`);
        console.log('─────────────────────────────────────────────');

        if (guidance.generation_method === 'groq_ai') {
            console.log('%c✅ Groq AI is WORKING correctly!', 'color: #10b981; font-weight: bold;');
            showGenerationBadge('groq', '✅ Powered by Groq AI');
        } else if (guidance.generation_method === 'template') {
            console.warn('%c⚠️ Groq FAILED — using template fallback', 'color: #f59e0b; font-weight: bold;');
            showGenerationBadge('template', '⚠️ Template Fallback (Groq unavailable)');
        } else if (guidance.generation_method === 'intelligent_fallback') {
            console.warn('%c⚠️ No docs found — using intelligent fallback', 'color: #f59e0b; font-weight: bold;');
            showGenerationBadge('fallback', '⚠️ Intelligent Fallback');
        }
        // ───────────────────────────────────────────────────

        const text = guidance.guidance || guidance.response || 'No response received.';
        responseContent.innerHTML = `<div style="padding:1rem; white-space: pre-wrap;">${text}</div>`;

    } catch (error) {
        console.error('%c❌ Guidance request FAILED', 'color: #ef4444; font-weight: bold;', error);
        showGenerationBadge('error', '❌ Request Failed');
        responseContent.innerHTML = '<p style="color:#ef4444;">Sorry, unable to get guidance. Check console for details.</p>';
    }
}

// ─── Helper: show a small badge above the response showing generation method ───
function showGenerationBadge(type, label) {
    // Remove any existing badge
    const existing = document.getElementById('generationBadge');
    if (existing) existing.remove();

    const colors = {
        loading:  { bg: '#e0e7ff', text: '#4f46e5' },
        groq:     { bg: '#d1fae5', text: '#065f46' },
        template: { bg: '#fef3c7', text: '#92400e' },
        fallback: { bg: '#fef3c7', text: '#92400e' },
        error:    { bg: '#fee2e2', text: '#991b1b' }
    };

    const color = colors[type] || colors.loading;
    const badge = document.createElement('div');
    badge.id = 'generationBadge';
    badge.style.cssText = `
        display: inline-block;
        margin: 0.5rem 0 0.25rem 0;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        background: ${color.bg};
        color: ${color.text};
    `;
    badge.textContent = label;

    // Insert badge before the response content
    const responseDiv = document.getElementById('guidanceResponse');
    if (responseDiv) {
        const existing = document.getElementById('generationBadge');
        if (existing) existing.remove();
        responseDiv.insertBefore(badge, responseDiv.firstChild);
    }
}

// Reset form
function resetForm() {
    document.getElementById('burnoutForm').reset();
    document.querySelector('.results-section').style.display = 'none';
    document.querySelectorAll('input[type="range"]').forEach(input => {
        const display = document.getElementById(input.id + '_value');
        if (display) display.textContent = input.value;
    });
    document.getElementById('responseContent').innerHTML = 'Ask me anything about wellness and burnout prevention!';

    // Remove badge on reset
    const badge = document.getElementById('generationBadge');
    if (badge) badge.remove();
}

// Load historical data
function loadHistoricalData() {
    updateTrendChart('Medium');
}

// ==================== EMAIL SUBSCRIPTION FUNCTIONS ====================

// Check and show email section
async function checkAndShowEmailSection() {
    const userId = localStorage.getItem('burnout_user_id');
    if (userId && !userId.startsWith('LOCAL_')) {
        const emailSection = document.getElementById('emailSection');
        if (emailSection) {
            emailSection.style.display = 'block';
        }
    }
}

// Subscribe to notifications
async function subscribeToNotifications(email, receiveWeekly, receiveAlerts) {
    const userId = localStorage.getItem('burnout_user_id');
    if (!userId || userId.startsWith('LOCAL_')) {
        showNotification('Please complete an assessment first to create your account.', 'warning');
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/user/subscribe?user_id=${userId}&email=${encodeURIComponent(email)}&receive_weekly=${receiveWeekly}&receive_alerts=${receiveAlerts}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Successfully subscribed to email notifications!', 'success');
            return true;
        } else {
            throw new Error('Subscription failed');
        }
    } catch (error) {
        console.error('Subscription error:', error);
        showNotification('Failed to subscribe. Please try again.', 'warning');
        return false;
    }
}

// Send weekly report email
async function sendWeeklyReport() {
    const userId = localStorage.getItem('burnout_user_id');
    
    if (!userId || userId.startsWith('LOCAL_')) {
        showNotification('Please complete an assessment first to create your account.', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/history/${userId}?limit=1`);
        const data = await response.json();
        
        if (!data.history || data.history.length === 0) {
            showNotification('No assessments found. Please analyze some data first.', 'warning');
            return;
        }
    } catch (error) {
        console.error('Error checking history:', error);
    }
    
    const sendBtn = document.getElementById('sendReportBtn');
    const originalText = sendBtn.innerHTML;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/send/weekly-report?user_id=${userId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('✅ Weekly report sent to your email!', 'success');
        } else {
            showNotification('❌ Failed to send report. Please check your email subscription.', 'warning');
        }
    } catch (error) {
        console.error('Error sending report:', error);
        showNotification('❌ Error sending report. Please try again.', 'warning');
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = originalText;
    }
}

// Initialize subscription form
function initSubscriptionForm() {
    const form = document.getElementById('subscriptionForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('userEmail').value;
            const receiveWeekly = document.getElementById('receiveWeekly').checked;
            const receiveAlerts = document.getElementById('receiveAlerts').checked;
            
            const subscribeBtn = document.getElementById('subscribeBtn');
            subscribeBtn.disabled = true;
            subscribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subscribing...';
            
            await subscribeToNotifications(email, receiveWeekly, receiveAlerts);
            
            subscribeBtn.disabled = false;
            subscribeBtn.innerHTML = '<i class="fas fa-bell"></i> Subscribe';
        });
    }
    
    // Add send report button listener
    const sendReportBtn = document.getElementById('sendReportBtn');
    if (sendReportBtn) {
        sendReportBtn.addEventListener('click', sendWeeklyReport);
    }
}

// Global error handler
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ' + msg);
    return false;
};