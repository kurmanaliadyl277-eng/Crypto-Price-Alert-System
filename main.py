import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from datetime import datetime
import tkinter.messagebox as msg

# Включаем тёмную тему и синий акцент
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CryptoAlertApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Crypto Price Alert System")
        self.geometry("1050x650")
        self.minsize(900, 550)

        # Делим окно на 2 колонки: слева управление, справа график
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        self.setup_left_panel()
        self.setup_right_panel()

        # Состояние мониторинга
        self.is_running = False
        self.price_log = []
        self.check_count = 0

        # Используем after() вместо threading — это штатный механизм tkinter
        self.after_id = None

    def setup_left_panel(self):
        """Левая часть: поля ввода, кнопки, лог"""
        left = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1b26")
        left.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        ctk.CTkLabel(left, text="⚡ Crypto Alert", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)

        # Поле крипты
        ctk.CTkLabel(left, text="Криптовалюта (ID):").pack(anchor="w", padx=15)
        self.crypto_entry = ctk.CTkEntry(left, placeholder_text="bitcoin, ethereum, solana...")
        self.crypto_entry.pack(fill="x", padx=15, pady=5)

        # Поле цены
        ctk.CTkLabel(left, text="Целевая цена ($):").pack(anchor="w", padx=15)
        self.price_entry = ctk.CTkEntry(left, placeholder_text="60000.00")
        self.price_entry.pack(fill="x", padx=15, pady=5)

        # Направление
        self.dir_var = ctk.StringVar(value="below")
        ctk.CTkLabel(left, text="Направление:").pack(anchor="w", padx=15)
        radio_box = ctk.CTkFrame(left, fg_color="transparent")
        radio_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkRadioButton(radio_box, text="Выше", variable=self.dir_var, value="above").pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_box, text="Ниже", variable=self.dir_var, value="below").pack(side="left", padx=10)

        # Кнопка старта/стопа
        self.btn_start = ctk.CTkButton(left, text="🚀 Запустить мониторинг", command=self.toggle_monitor)
        self.btn_start.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(left, text="🗑 Очистить лог", fg_color="transparent", border_width=1, command=self.clear_log).pack(
            fill="x", padx=15)

        # Область лога
        ctk.CTkLabel(left, text="📜 История проверок:").pack(anchor="w", padx=15, pady=(10, 5))
        self.log_box = ctk.CTkTextbox(left, height=250)
        self.log_box.pack(fill="both", padx=15, pady=5)
        self.log_box.configure(state="disabled")

    def setup_right_panel(self):
        """Правая часть: график цены"""
        right = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1b26")
        right.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        # Создаём график matplotlib
        self.fig, self.ax = plt.subplots(figsize=(6, 5), dpi=100)
        self.ax.set_facecolor("#24283b")
        self.fig.patch.set_facecolor("#24283b")
        self.ax.set_title("Динамика цены", color="white", pad=10)
        self.ax.grid(True, color="#414868", linestyle="--", alpha=0.5)
        self.ax.tick_params(colors="white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.draw_empty_chart()

    def toggle_monitor(self):
        """Запуск или остановка проверки"""
        if not self.is_running:
            self.crypto = self.crypto_entry.get().lower().strip()
            try:
                self.target = float(self.price_entry.get())
            except ValueError:
                msg.showwarning("Ошибка", "Введите корректную цену!")
                return

            if not self.crypto:
                msg.showwarning("Ошибка", "Введите ID криптовалюты!")
                return

            self.price_log = []
            self.check_count = 0
            self.dir = self.dir_var.get()

            # Меняем вид кнопки
            self.btn_start.configure(text=" Остановить", fg_color="#e74c3c")
            self.is_running = True
            self.log(f"🟡 Старт: мониторим {self.crypto.upper()} каждые 30 сек...")

            # Запускаем первый цикл
            self.schedule_check()
        else:
            self.is_running = False
            if self.after_id:
                self.after_cancel(self.after_id)
            self.btn_start.configure(text="🚀 Запустить мониторинг", fg_color="#3498db")
            self.log("🔴 Мониторинг остановлен")

    def schedule_check(self):
        """Штатный таймер tkinter (не блокирует интерфейс)"""
        if self.is_running:
            self.check_price()
            # Перезапускаем через 30 секунд
            self.after_id = self.after(30000, self.schedule_check)

    def check_price(self):
        """Запрашиваем цену, сравниваем с целью, обновляем график"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self.crypto}&vs_currencies=usd"
            res = requests.get(url, timeout=10)

            # 🔧 ИСПРАВЛЕНИЕ: Проверяем статус ответа
            if res.status_code != 200:
                self.log(f"️ API Error: {res.status_code} (Подождите...)")
                return

            data = res.json()

            #  ИСПРАВЛЕНИЕ: Проверяем, не вернул ли API ошибку (лимит запросов)
            if "error" in data:
                self.log(f"⚠️ API Error: {data['error']} (Подождите 1 мин)")
                return

            # Если всё ок и данные есть
            if self.crypto in data:
                current = data[self.crypto]['usd']
                time_str = datetime.now().strftime("%H:%M:%S")
                self.check_count += 1

                # Сохраняем для графика
                self.price_log.append(current)

                # Проверяем условие алерта
                hit = (self.dir == "above" and current >= self.target) or \
                      (self.dir == "below" and current <= self.target)

                status = "🚨 АЛЕРТ" if hit else "✅ OK"
                self.log(f"{time_str} | {self.crypto.upper()} | ${current:.2f} | {status}")

                # Если алерт сработал — показываем окно и останавливаем
                if hit:
                    msg.showinfo("🚨 Алерт!", f"Цена {self.crypto.upper()} достигла цели!\n${current:.2f}")
                    self.toggle_monitor()

                self.update_chart(current, hit)
            else:
                self.log(f"❌ '{self.crypto}' нет в ответе API")
        except Exception as e:
            self.log(f"⚠️ Сетевая ошибка: {e}")

    def update_chart(self, current_price, is_alert=False):
        """Перерисовываем график с новыми точками"""
        self.ax.clear()
        self.ax.set_facecolor("#24283b")
        self.fig.patch.set_facecolor("#24283b")

        # Рисуем линию цены
        x = list(range(len(self.price_log)))
        color = "#e74c3c" if is_alert else "#3498db"
        self.ax.plot(x, self.price_log, color=color, marker="o", linewidth=2, markersize=6)
        self.ax.fill_between(x, self.price_log, alpha=0.2, color=color)

        # Рисуем горизонтальную линию цели
        self.ax.axhline(y=self.target, color="#f1c40f", linestyle="--", label=f"Цель: ${self.target}")
        self.ax.legend(facecolor="#24283b", edgecolor="white", labelcolor="white")

        self.ax.tick_params(colors="white")
        self.ax.grid(True, color="#414868", linestyle="--", alpha=0.5)
        self.ax.set_title(f"{self.crypto.upper()} — Проверка #{self.check_count}", color="white", pad=10)
        self.fig.tight_layout()
        self.canvas.draw()

    def draw_empty_chart(self):
        """Показываем пустой график при старте"""
        self.ax.set_xlabel("Номер проверки", color="white")
        self.ax.set_ylabel("Цена ($)", color="white")
        self.canvas.draw()

    def log(self, text):
        """Добавляем строку в лог-окно"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    app = CryptoAlertApp()
    app.mainloop()