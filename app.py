import streamlit as st

from pawpal_ai import PawPalAI
from pawpal_system import Owner, Pet, Scheduler, Task, load_from_json, save_to_json


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

PRIORITY_MAP = {"low": 1, "medium": 2, "high": 3}
PRIORITY_LABEL = {1: "low", 2: "medium", 3: "high"}


def clear_generated_results() -> None:
    st.session_state.generated_plan = None
    st.session_state.skipped_tasks = []
    st.session_state.ai_guidance = None


if "owner" not in st.session_state:
    st.session_state.owner = load_from_json()
if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None
    st.session_state.skipped_tasks = []
    st.session_state.planned_available_time = 0
    st.session_state.ai_guidance = None


st.subheader("Step 1 — Owner & Pet Info")
col1, col2, col3 = st.columns(3)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
with col3:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Save owner & pet"):
    owner = Owner(name=owner_name)
    owner.add_pet(Pet(name=pet_name, species=species))
    st.session_state.owner = owner
    clear_generated_results()
    save_to_json(owner)
    st.success(f"Saved! Owner: {owner_name} | Pet: {pet_name} ({species})")

st.divider()

if st.session_state.owner is None:
    st.info("Fill in owner and pet info above, then click Save owner & pet to get started.")
    st.stop()

owner = st.session_state.owner
pets = owner.get_pets()


st.subheader("Step 2 — Add Tasks")
pet_names = [pet.get_name() for pet in pets]
selected_pet_name = st.selectbox("Add task to", pet_names)
selected_pet = next(pet for pet in pets if pet.get_name() == selected_pet_name)

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_name = st.text_input("Task name", value="Morning walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
with col3:
    priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    start_time_input = st.text_input(
        "Start time (HH:MM)", value="", placeholder="e.g. 08:00"
    )

if st.button("Add task"):
    selected_pet.add_task(
        Task(
            routine_name=task_name,
            frequency="daily",
            duration=int(duration),
            priority=PRIORITY_MAP[priority_label],
            start_time=start_time_input.strip() or None,
        )
    )
    clear_generated_results()
    save_to_json(owner)
    st.success(f"Added '{task_name}' to {selected_pet_name}")

for pet in pets:
    tasks = pet.get_tasks()
    if tasks:
        st.markdown(f"**{pet.get_name()}'s tasks**")
        st.table(
            [
                {
                    "Task": task.get_routine_name(),
                    "Duration (min)": task.get_duration(),
                    "Priority": PRIORITY_LABEL[task.get_priority()],
                    "Start time": task.start_time or "—",
                    "Done": "yes" if task.is_completed() else "no",
                }
                for task in tasks
            ]
        )

st.divider()


st.subheader("Step 3 — Generate Schedule")
available_time = st.number_input(
    "Available time today (minutes)", min_value=10, max_value=480, value=90
)

if st.button("Generate schedule"):
    scheduler = Scheduler(owner=owner, available_time=int(available_time))
    plan = scheduler.generate()
    all_tasks = scheduler.get_all_tasks()
    skipped = [task for task in all_tasks if task not in plan]

    start_hour, start_minute = 8, 0
    for task in plan:
        task.start_time = f"{start_hour:02d}:{start_minute:02d}"
        start_minute += task.get_duration()
        start_hour += start_minute // 60
        start_minute %= 60

    st.session_state.generated_plan = scheduler.sort_by_time(plan)
    st.session_state.skipped_tasks = skipped
    st.session_state.planned_available_time = int(available_time)
    st.session_state.ai_guidance = None

generated_plan = st.session_state.generated_plan
if generated_plan is not None:
    if not generated_plan:
        st.warning(
            "No tasks fit in the available time. Try adding shorter tasks or increasing available time."
        )
    else:
        used_time = sum(task.get_duration() for task in generated_plan)
        planned_time = st.session_state.planned_available_time
        st.success(
            f"Today's plan for {owner.get_name()}'s pets — "
            f"{used_time} / {planned_time} min used"
        )
        st.table(
            [
                {
                    "Time": task.start_time,
                    "Task": task.get_routine_name(),
                    "Duration (min)": task.get_duration(),
                    "Priority": PRIORITY_LABEL[task.get_priority()],
                }
                for task in generated_plan
            ]
        )
        st.caption(
            f"Scheduled {len(generated_plan)} of {len(owner.get_all_tasks())} tasks."
        )

        conflicts = Scheduler(owner, planned_time).detect_conflicts(generated_plan)
        if conflicts:
            st.markdown("#### Scheduling Conflicts")
            for warning in conflicts:
                st.warning(warning)
        else:
            st.success("No scheduling conflicts detected.")

        skipped_tasks = st.session_state.skipped_tasks
        if skipped_tasks:
            with st.expander(
                f"Skipped tasks ({len(skipped_tasks)}) — did not fit in available time"
            ):
                st.table(
                    [
                        {
                            "Task": task.get_routine_name(),
                            "Duration (min)": task.get_duration(),
                            "Priority": PRIORITY_LABEL[task.get_priority()],
                        }
                        for task in skipped_tasks
                    ]
                )

st.divider()


st.subheader("Step 4 — Ask PawPal AI About the Plan")
st.caption(
    "PawPal retrieves relevant passages from its local care guide before the AI "
    "answers. It is a planning assistant, not a veterinarian."
)

if not generated_plan:
    st.info("Generate a schedule first so the AI can explain that specific plan.")
else:
    ai_question = st.text_area(
        "Question about today's plan",
        value="How can I make this care plan easier to follow?",
        max_chars=500,
    )
    if st.button("Get grounded AI guidance"):
        st.session_state.ai_guidance = PawPalAI().generate_guidance(
            owner=owner,
            plan=generated_plan,
            question=ai_question,
        )

    guidance = st.session_state.ai_guidance
    if guidance is not None:
        if guidance.guardrail_triggered:
            st.error(guidance.answer)
        elif guidance.error:
            st.warning(guidance.answer)
        else:
            st.markdown(guidance.answer)

        st.metric("Retrieval confidence", f"{guidance.confidence:.0%}")
        if guidance.sources:
            with st.expander("Retrieved sources used by PawPal AI"):
                for source in guidance.sources:
                    st.markdown(f"**[{source.id}] {source.source}**")
                    st.write(source.content)

st.divider()


st.subheader("Step 5 — View Tasks by Status")
scheduler = Scheduler(owner=owner, available_time=0)
col1, col2 = st.columns(2)

with col1:
    pending = scheduler.filter_by_status(completed=False)
    st.markdown(f"**Pending ({len(pending)})**")
    if pending:
        st.table(
            [
                {
                    "Task": task.get_routine_name(),
                    "Priority": PRIORITY_LABEL[task.get_priority()],
                }
                for task in pending
            ]
        )
    else:
        st.info("All tasks completed!")

with col2:
    completed = scheduler.filter_by_status(completed=True)
    st.markdown(f"**Completed ({len(completed)})**")
    if completed:
        st.table(
            [
                {
                    "Task": task.get_routine_name(),
                    "Priority": PRIORITY_LABEL[task.get_priority()],
                }
                for task in completed
            ]
        )
    else:
        st.info("No completed tasks yet.")
