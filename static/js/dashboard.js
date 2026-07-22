// Dashboard Visualization and Charting Engine

document.addEventListener("DOMContentLoaded", function () {
    // Check if dashboard canvas elements exist before initializing
    const expenseCtx = document.getElementById("expenseChart");
    const timelineCtx = document.getElementById("timelineChart");
    const trendsCtx = document.getElementById("trendsChart");
    const predictionCtx = document.getElementById("predictionChart");

    // Dynamic Chart Colors (vibrant HSL palette)
    const colorPalette = [
        '#6366f1', // indigo
        '#a855f7', // purple
        '#ec4899', // pink
        '#10b981', // emerald
        '#f59e0b', // amber
        '#3b82f6', // blue
        '#ef4444', // red
        '#14b8a6', // teal
        '#64748b'  // slate
    ];

    // Check theme colors to style grids correctly
    const isDarkTheme = document.body.classList.contains("dark-theme");
    const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';
    const labelColor = isDarkTheme ? '#9ca3af' : '#4b5563';

    // 1. Fetch & Initialize Dashboard Charts
    if (expenseCtx || timelineCtx || trendsCtx) {
        fetch("/api/dashboard_data")
            .then(response => response.json())
            .then(data => {
                // If there's no data, do not draw charts to avoid console errors
                if (!data.category_labels || data.category_labels.length === 0) {
                    return;
                }

                // A. Expense Category Pie Chart
                if (expenseCtx) {
                    new Chart(expenseCtx, {
                        type: 'doughnut',
                        data: {
                            labels: data.category_labels,
                            datasets: [{
                                data: data.category_values,
                                backgroundColor: colorPalette,
                                borderWidth: 2,
                                borderColor: 'transparent'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'right',
                                    labels: {
                                        color: labelColor,
                                        font: { family: 'Outfit', size: 12 }
                                    }
                                },
                                tooltip: {
                                    padding: 12,
                                    bodyFont: { family: 'Outfit' },
                                    titleFont: { family: 'Outfit', weight: 'bold' }
                                }
                            },
                            cutout: '65%'
                        }
                    });
                }

                // B. Income vs Expense Comparison Bar Chart (Grouped)
                if (timelineCtx) {
                    new Chart(timelineCtx, {
                        type: 'bar',
                        data: {
                            labels: data.timeline_labels,
                            datasets: [
                                {
                                    label: 'Income',
                                    data: data.timeline_income,
                                    backgroundColor: 'rgba(16, 185, 129, 0.85)',
                                    borderRadius: 6
                                },
                                {
                                    label: 'Expense',
                                    data: data.timeline_expense,
                                    backgroundColor: 'rgba(244, 63, 94, 0.85)',
                                    borderRadius: 6
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { color: labelColor, font: { family: 'Outfit' } }
                                },
                                y: {
                                    grid: { color: gridColor },
                                    ticks: { color: labelColor, font: { family: 'Outfit' } }
                                }
                            },
                            plugins: {
                                legend: {
                                    position: 'top',
                                    labels: { color: labelColor, font: { family: 'Outfit' } }
                                }
                            }
                        }
                    });
                }

                // C. Trend Analysis Timeline Chart (Line Chart of expenses)
                if (trendsCtx) {
                    new Chart(trendsCtx, {
                        type: 'line',
                        data: {
                            labels: data.timeline_labels,
                            datasets: [{
                                label: 'Monthly Expenses Trend',
                                data: data.timeline_expense,
                                borderColor: '#6366f1',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                fill: true,
                                tension: 0.4,
                                borderWidth: 3,
                                pointBackgroundColor: '#6366f1',
                                pointHoverRadius: 6
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { color: labelColor, font: { family: 'Outfit' } }
                                },
                                y: {
                                    grid: { color: gridColor },
                                    ticks: { color: labelColor, font: { family: 'Outfit' } }
                                }
                            },
                            plugins: {
                                legend: { display: false }
                            }
                        }
                    });
                }
            })
            .catch(err => console.error("Error loading dashboard charts data:", err));
    }

    // 2. Fetch & Initialize Machine Learning Prediction Charts
    if (predictionCtx) {
        fetch("/api/predictions")
            .then(response => response.json())
            .then(data => {
                if (!data.cat_labels || data.cat_labels.length === 0) {
                    // Draw dummy warning in chart context
                    return;
                }

                // D. Projected Category Expenses next month (Horizontal Bar Chart)
                new Chart(predictionCtx, {
                    type: 'bar',
                    data: {
                        labels: data.cat_labels,
                        datasets: [{
                            label: 'Projected Spend next month (₹)',
                            data: data.cat_values,
                            backgroundColor: 'rgba(168, 85, 247, 0.8)',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                grid: { color: gridColor },
                                ticks: { color: labelColor, font: { family: 'Outfit' } }
                            },
                            y: {
                                grid: { display: false },
                                ticks: { color: labelColor, font: { family: 'Outfit' } }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                padding: 12,
                                bodyFont: { family: 'Outfit' }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error("Error loading ML prediction charts data:", err));
    }
});
