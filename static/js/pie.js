var  labels = {{ data1 | tojson | safe }};
                    var data = {{ gender_data | tojson | safe }};
                    // Pie Chart Example
                    var ctx = document.getElementById("genderChart");
                    var myPieChart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: labels,
                            datasets: [{
                                data: data,
                               backgroundColor: ['#ff5733', '#33ff57', '#5733ff'],
                                hoverBackgroundColor: ['#ff9966', '#66ff99', '#9966ff'],
                                hoverBorderColor: "rgba(255, 0, 0, 1)",

                            }],
                        },
                        options: {
                            maintainAspectRatio: false,
                            tooltips: {
                                backgroundColor: "rgb(255,255,255)",
                                bodyFontColor: "#858796",
                                borderColor: '#dddfeb',
                                borderWidth: 1,
                                xPadding: 15,
                                yPadding: 15,
                                displayColors: false,
                                caretPadding: 10,
                            },
                            legend: {
                                display: true
                            },
                            cutoutPercentage: 80,
                        },
                    });
