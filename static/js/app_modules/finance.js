function toggleSidebar() {
    const sidebar = document.getElementById('sidebar-section');
    sidebar.classList.toggle('d-none');
}
fetch('/finance/days_data')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log(data)
        populateTable(data);
    })
    .catch(error => {
        console.error('There was a problem with the fetch operation:', error);
    });

function getWeekday(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('en-us', { weekday: 'long' });
}
function populateTable(data) {
    const tbody = document.getElementById('table-body');

    for (const week in data) {
        const weekData = data[week];

        const dailySales = { "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0 };
        const dailyCOGS = { "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0 };

        weekData.sales.forEach(sale => {
            const day = getWeekday(sale.date);
            dailySales[day] += parseFloat(sale.total_amount);
        });

        weekData.cogs.forEach(cogs => {
            const day = getWeekday(cogs.date);
            dailyCOGS[day] += parseFloat(cogs.product__cost);
        });

        const totalSales = Object.values(dailySales).reduce((a, b) => a + b, 0);
        const totalCOGS = Object.values(dailyCOGS).reduce((a, b) => a + b, 0);
        const grossProfit = totalSales - totalCOGS;

        const salesRow = document.createElement('tr');
        const cogsRow = document.createElement('tr');
        const grossProfitRow = document.createElement('tr');
        const gapRow = document.createElement('tr');
        const daysRow = document.createElement('tr');

        salesRow.innerHTML = `<td></td><td class=''>Sales</td>`;
        cogsRow.innerHTML = `<td class='fw-bold'>${week}</td><td class='text-danger'>COS</td>`;
        grossProfitRow.innerHTML = `<td></td><td class=''>Gross Profit</td>`;
        gapRow.innerHTML += `<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>`;
        daysRow.innerHTML += `
                <td class="bg-primary text-light"></td>
                <td class="bg-primary text-light"></td>
                <td class="bg-primary text-light">Monday</td>
                <td class="bg-primary text-light">Tuesday</td>
                <td class="bg-primary text-light">Wednesday</td>
                <td class="bg-primary text-light">Thursday</td>
                <td class="bg-primary text-light">Friday</td>
                <td class="bg-primary text-light">Saturday</td>
                <td class="bg-primary text-light">Sunday</td>
                <td class="bg-primary text-light"></td>
            `;

        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].forEach(day => {
            salesRow.innerHTML += `<td>${dailySales[day].toFixed(2)}</td>`;
            cogsRow.innerHTML += `<td class='text-danger'>${dailyCOGS[day].toFixed(2)}</td>`;
            grossProfitRow.innerHTML += `<td>${(dailySales[day] - dailyCOGS[day]).toFixed(2)}</td>`;
        });

        salesRow.innerHTML += `<td class='fw-bold'>${totalSales.toFixed(2)}</td>`;
        cogsRow.innerHTML += `<td class='fw-bold  text-danger'>${totalCOGS.toFixed(2)}</td>`;
        grossProfitRow.innerHTML += `<td class='fw-bold' style='background#fcd298'>${grossProfit.toFixed(2)}</td>`;

        tbody.appendChild(salesRow);
        tbody.appendChild(cogsRow);
        tbody.appendChild(grossProfitRow);

        if (['week 1', 'week 2', 'week 3'].includes(week)) {
            tbody.appendChild(daysRow);
        }
    }
}

document.getElementById('timeFrame').addEventListener('change', function () {
    const customTimeFrame = document.getElementById('customTimeFrame');
    if (this.value === 'custom') {
        customTimeFrame.classList.remove('d-none');
    } else {
        customTimeFrame.classList.add('d-none');
    }
});

document.getElementById('timeFrameForm').addEventListener('submit', function (event) {
    event.preventDefault();

    const timeFrame = document.getElementById('timeFrame').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    let queryParams = new URLSearchParams({ timeFrame });

    if (timeFrame === 'custom') {
        queryParams.append('startDate', startDate);
        queryParams.append('endDate', endDate);
    }

    fetch(`generate-report/?${queryParams.toString()}`)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `income_statement_${timeFrame}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => console.error('Error generating report:', error));

    const timeFrameModal = new bootstrap.Modal(document.getElementById('timeFrameModal'));
    timeFrameModal.hide();
});

function fetchData(filter) {
    fetch(`/finance/income_json/?filter=${filter}`)
        .then(response => response.json())
        .then(data => {
            const sales = data.sales_total
            document.getElementById('id_income').textContent = `$${sales}`;
        });

    fetch(`/finance/expense_json/?filter=${filter}`)
        .then(response => response.json())
        .then(data => {
            const expenses = data.expense_total;
            document.getElementById('id_expense').textContent = `$${expenses}`;
        });

    fetch(`/finance/pl_overview/?filter=${filter}`)
        .then(response => response.json())
        .then(data => {
            const net_income = data.current_net_income;
            document.getElementById('net_income_amount').textContent = `$${net_income}`;
            document.getElementById('id_cogs').textContent = `$${data.cogs_total}`
            document.getElementById('id_gp_metrix_amount').textContent = `$${data.current_gross_profit}`
            document.getElementById('id_gpm_metrix').textContent = `${data.current_gross_profit_margin}%`
            document.getElementById('id_expenses_metrix_amount').textContent = `$${data.current_expenses}`
            document.getElementById('id_net_metrix_amount').textContent = `$${data.current_net_profit}`
            document.getElementById('pl_overview_total').textContent = `$${data.current_net_profit}`

            if (data.current_net_profit < 0) {
                document.getElementById('pl_overview_total').classList.add('text-danger')
                console.log(data.current_net_profit)
            }
        });
}
fetchData('today');
document.addEventListener('DOMContentLoaded', function () {

    {% comment %} const monthSelect = document.createElement('select');
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const currentMonth = new Date().getMonth();

    const currentMonthOption = document.createElement('option');
    currentMonthOption.value = currentMonth + 1;
    currentMonthOption.text = months[currentMonth];
    currentMonthOption.selected = true;
    monthSelect.appendChild(currentMonthOption);

    months.forEach((month, index) => {
        if (index !== currentMonth) {
            const option = document.createElement('option');
            option.value = index + 1;
            option.text = month;
            monthSelect.appendChild(option);
        }
    });

    const incomeMonthElement = document.getElementById('id_income_month');
    incomeMonthElement.innerHTML = '';
    incomeMonthElement.appendChild(monthSelect);

    monthSelect.addEventListener('change', function () {
        const selectedMonth = monthSelect.value;

        fetch(`/finance/income_json?month=${selectedMonth}`)
            .then(response => response.json())
            .then(data => {
                total_sales = parseFloat(data.sales_total)
                document.getElementById('id_income').innerText = `$${total_sales.toFixed(2)}`;
            });

        fetch(`/finance/expense_json?month=${selectedMonth}`)
            .then(response => response.json())
            .then(data => {
                total_expenses = parseFloat(data.expense_total)
                document.getElementById('id_expense').innerText = `$${total_expenses.toFixed(2)}`;
            });
    });
    monthSelect.dispatchEvent(new Event('change'));
    {% endcomment %}

    // graphs

    Chart.register({
        id: 'customCanvasBackgroundColor',
        beforeDraw: (chart) => {
            const ctx = chart.canvas.getContext('2d');
            ctx.save();
            ctx.globalCompositeOperation = 'destination-over';
            ctx.fillStyle = chart.config.options.plugins.customCanvasBackgroundColor.color || '#ffffff';
            ctx.fillRect(0, 0, chart.width, chart.height);
            ctx.color
            ctx.restore();
        }
    });

    const monthLabels = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    function fetchAndRenderChart(url, ctx, chartLabel) {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const chartData = monthLabels.map((label, index) => data[index + 1] || 0);
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: monthLabels,
                        datasets: [{
                            label: chartLabel,
                            data: chartData,
                            backgroundColor: 'transparent',
                            borderColor: '#dedede',
                            borderWidth: 1,
                            pointRadius: 0,
                            pointHoverRadius: 0
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    color: 'white'
                                },
                                grid: {
                                    color: '#111'
                                }
                            },
                            x: {
                                ticks: {
                                    color: '#fff'
                                },
                                grid: {
                                    color: '#111'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                labels: {
                                    color: 'white' // Color of legend text
                                }
                            },
                            customCanvasBackgroundColor: {
                                color: '#111' // Background color of the chart area
                            }
                        },
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            });
    }

    const incomeCtx = document.getElementById('incomeChart').getContext('2d');
    fetchAndRenderChart('/finance/income_graph/', incomeCtx, 'Monthly Income');

    const expenseCtx = document.getElementById('expenseChart').getContext('2d');
    fetchAndRenderChart('/finance/expense_graph/', expenseCtx, 'Monthly Expenses');

});
