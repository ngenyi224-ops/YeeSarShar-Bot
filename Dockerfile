FROM python:3.10-slim

WORKDIR /app

# လိုအပ်သော library များသွင်းရန် requirements.txt ကို အရင်ကူးပါ
COPY requirements.txt .

# Library များကို install လုပ်ပါ
RUN pip install --no-cache-dir -r requirements.txt

# ကျန်ရှိသော code အားလုံးကို ကူးပါ
COPY . .

# Bot ကို စတင် run ရန်
CMD ["python", "main.py"]
