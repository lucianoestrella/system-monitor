def run_full_stress(self):
    """Executa stress test PESADO (CPU + RAM)."""
    try:
        duration = float(self.full_duration_entry.get())
        intensity = float(self.full_intensity_entry.get())

        # Limita duração a 600s
        if duration > 600:
            duration = 600.0

        self.full_stress_btn.configure(state="disabled", text="⚠️ EXECUTANDO STRESS PESADO ⚠️")

        def stress_thread():
            start_full_stress(duration=duration, cpu_intensity=intensity)
            self.full_stress_btn.configure(state="normal", text="🔥 INICIAR STRESS PESADO 🔥")

        threading.Thread(target=stress_thread, daemon=True).start()

    except ValueError:
        pass