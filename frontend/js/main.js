// Constants
const API_URL = 'http://localhost:8000';
const USER_ID = 1; // This should be dynamic based on your needs

// Chart colors
const CHART_COLORS = {
    easy: '#2ecc71',
    medium: '#f1c40f',
    hard: '#e74c3c',
    leetcode: '#FFA116',
    codechef: '#5B4638',
    codeforces: '#1F8ACB'
};

// Initialize charts
let ratingChart;
let dsaChart;

// Fetch user stats
async function fetchUserStats() {
    try {
        const response = await fetch(`${API_URL}/user/${USER_ID}/stats`);
        if (!response.ok) throw new Error('Failed to fetch user stats');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error fetching user stats:', error);
    }
}

// Update UI with fetched data
function updateUI(data) {
    // Update total stats
    document.querySelector('.total-questions').textContent = data.total_problems_solved || 0;
    
    // Update platform-specific stats
    updatePlatformStats(data.platform_stats);
    
    // Update charts
    updateDSAChart(data.platform_stats.leetcode);
    updateRatingChart(data.platform_stats);
    
    // Update rankings
    updateRankings(data.platform_stats);
    
    // Update topic analysis
    if (data.platform_stats.codeforces.problem_tags) {
        updateTopicAnalysis(data.platform_stats.codeforces.problem_tags);
    }
}

// Update platform statistics
function updatePlatformStats(stats) {
    if (stats.leetcode) {
        document.querySelector('.leetcode .platform-count').textContent = stats.leetcode.total_solved || 0;
    }
    if (stats.codechef) {
        document.querySelector('.codechef .platform-count').textContent = stats.codechef.total_solved || 0;
    }
    if (stats.codeforces) {
        document.querySelector('.codeforces .platform-count').textContent = stats.codeforces.total_solved || 0;
    }
}

// Update DSA distribution chart
function updateDSAChart(leetcodeStats) {
    if (!leetcodeStats) return;

    const ctx = document.getElementById('dsaChart').getContext('2d');
    
    if (dsaChart) {
        dsaChart.destroy();
    }

    dsaChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Easy', 'Medium', 'Hard'],
            datasets: [{
                data: [
                    leetcodeStats.easy_solved || 0,
                    leetcodeStats.medium_solved || 0,
                    leetcodeStats.hard_solved || 0
                ],
                backgroundColor: [
                    CHART_COLORS.easy,
                    CHART_COLORS.medium,
                    CHART_COLORS.hard
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            cutout: '70%'
        }
    });

    // Update stats numbers
    document.querySelector('.easy .count').textContent = leetcodeStats.easy_solved || 0;
    document.querySelector('.medium .count').textContent = leetcodeStats.medium_solved || 0;
    document.querySelector('.hard .count').textContent = leetcodeStats.hard_solved || 0;
}

// Update rating chart
function updateRatingChart(stats) {
    const ctx = document.getElementById('ratingChart').getContext('2d');
    
    if (ratingChart) {
        ratingChart.destroy();
    }

    // Sample data - you'll need to implement actual rating history
    const ratings = {
        leetcode: stats.leetcode.contest_rating || 0,
        codechef: stats.codechef.rating || 0,
        codeforces: stats.codeforces.rating || 0
    };

    ratingChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['LeetCode', 'CodeChef', 'CodeForces'],
            datasets: [{
                label: 'Rating',
                data: Object.values(ratings),
                borderColor: CHART_COLORS.leetcode,
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Update rankings section
function updateRankings(stats) {
    // LeetCode
    if (stats.leetcode) {
        document.querySelector('.leetcode .rating').textContent = stats.leetcode.contest_rating || 0;
        document.querySelector('.leetcode .max-rating').textContent = 
            `(max: ${stats.leetcode.contest_rating || 0})`;
    }

    // CodeChef
    if (stats.codechef) {
        document.querySelector('.codechef .rating').textContent = stats.codechef.rating || 0;
        document.querySelector('.codechef .max-rating').textContent = 
            `(max: ${stats.codechef.highest_rating || 0})`;
    }

    // CodeForces
    if (stats.codeforces) {
        document.querySelector('.codeforces .rating').textContent = stats.codeforces.rating || 0;
        document.querySelector('.codeforces .max-rating').textContent = 
            `(max: ${stats.codeforces.rating || 0})`;
        document.querySelector('.codeforces .rank').textContent = 
            stats.codeforces.rank || 'unrated';
    }
}

// Update topic analysis
function updateTopicAnalysis(tags) {
    const topicBars = document.getElementById('topicBars');
    topicBars.innerHTML = '';

    // Sort tags by count in descending order
    const sortedTags = Object.entries(tags)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10); // Show top 10 topics

    const maxCount = Math.max(...sortedTags.map(([,count]) => count));

    sortedTags.forEach(([topic, count]) => {
        const percentage = (count / maxCount) * 100;
        
        const topicBar = document.createElement('div');
        topicBar.className = 'topic-bar';
        topicBar.innerHTML = `
            <div class="topic-name">${topic}</div>
            <div class="bar-container">
                <div class="bar" style="width: ${percentage}%"></div>
            </div>
            <div class="topic-count">${count}</div>
        `;
        
        topicBars.appendChild(topicBar);
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchUserStats();
}); 