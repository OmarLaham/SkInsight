// SkinProfileChart
const ctx = document.getElementById('skinProfileChart').getContext('2d');


const chartData = JSON.parse(document.getElementById("care-chart-js-data").textContent); // care-chart-js-data is populated in the template using context 
const datasets = chartData.datasets;
const labels = chartData.labels; // Represent timeponits (quiz submissions)

const n_questions = datasets.length;


const quizChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: labels,
    datasets: datasets
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        title: {
          display: true,
          text: "Result / 10",
          font: {
            size: 14,
            weight: 'bold'
          }
        },
        //beginAtZero: true,
        min: 1, 
        max: 10,
        ticks: {
          stepSize: 1,
          max: 10
        },
        grid: {
          color: "#e5e7eb"
        }
      },
      x: {
      title: {
        display: true,
        text: "Check up",
        font: {
          size: 14,
          weight: 'bold'
        }
      }, grid: {
          color: "#f3f4f6"
        }
      }
    },
    plugins: {
      tooltip: {
        enabled: true,
        callbacks: {
          label: function(context) {
            return context.dataset.label + " - Progress: " + context.parsed.y;
          }
        }
      },
      legend: {
        display: false
      }
    }
  }
});
