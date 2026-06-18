let matchesData;
let drifaData;
let bruolData;
let workouts = [];
let dataReady = false;
let loadError = false;

const CREAM = "#eee7dc";
const ORANGE = "#d67c4b";
const BLACK = "#20201f";

function setup() {
    createCanvas(800, 1131);
    pixelDensity(new URLSearchParams(window.location.search).has("print") ? 6 : 2);
    textFont("Bauhaus, Crescendo Display, sans-serif");
    noLoop();
    redraw();
    loadWorkoutData();
}

async function loadWorkoutData() {
    try {
        const responses = await Promise.all([
            fetch("outputs/workout_matches.json"),
            fetch("outputs/drifa.json"),
            fetch("outputs/bruol.json"),
        ]);

        if (responses.some((response) => !response.ok)) throw new Error("Workout data could not be loaded");

        [matchesData, drifaData, bruolData] = await Promise.all(
            responses.map((response) => response.json())
        );
        buildWorkoutData();
        dataReady = true;
        document.body.dataset.posterReady = "true";
        redraw();
    } catch (error) {
        console.error(error);
        loadError = true;
        redraw();
    }
}

function buildWorkoutData() {
    const drifaWorkouts = Array.isArray(drifaData) ? drifaData : Object.values(drifaData);
    const bruolWorkouts = Array.isArray(bruolData) ? bruolData : Object.values(bruolData);
    const byId = new Map([...drifaWorkouts, ...bruolWorkouts].map((workout) => [workout.id, workout]));

    workouts = matchesData.matches
        .map((match) => {
            const left = byId.get(match.left.id);
            const right = byId.get(match.right.id);
            return {
                date: new Date(match.left.start_time),
                drifaVolume: Number(left?.estimated_volume_kg) || 0,
                bruolVolume: Number(right?.estimated_volume_kg) || 0,
                name: match.left.name,
            };
        })
        .sort((a, b) => a.date - b.date);
}

function draw() {
    background(CREAM);
    fill(BLACK);
    noStroke();

    if (!dataReady) {
        textAlign(CENTER, CENTER);
        textStyle(NORMAL);
        textSize(24);
        text(loadError ? "WORKOUT DATA UNAVAILABLE" : "LOADING WORKOUTS", width / 2, height / 2);
        return;
    }

    const left = 64;
    const right = width - 64;
    const chartTop = 160;
    const baseline = 1000;

    textStyle(NORMAL);
    textSize(74);
    textAlign(LEFT, TOP);
    fill(BLACK);
    text("DRIFA", left, 58);
    textAlign(RIGHT, TOP);
    fill(ORANGE);
    text("BRUOL", right, 58);

    const totals = workouts.map((d) => d.drifaVolume + d.bruolVolume);
    const maxTotal = Math.max(...totals, 1);
    const slotWidth = (right - left) / workouts.length;
    const totalHeight = baseline - chartTop;

    for (let i = 0; i < workouts.length; i++) {
        const item = workouts[i];
        const total = item.drifaVolume + item.bruolVolume;
        const barWidth = map(sqrt(total), 0, sqrt(maxTotal), 2.5, slotWidth * 0.78);
        const x = left + i * slotWidth + (slotWidth - barWidth) / 2;
        const drifaHeight = total > 0 ? totalHeight * (item.drifaVolume / total) : 0;
        const bruolHeight = totalHeight - drifaHeight;

        fill(BLACK);
        rect(x, baseline - drifaHeight, barWidth, drifaHeight);
        fill(ORANGE);
        rect(x, baseline - totalHeight, barWidth, bruolHeight);
    }

}
