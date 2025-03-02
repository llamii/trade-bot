## 📌 Трейдинг-бот для Bybit  

### Стратегия  
Бот использует индикаторы **EMA (5, 10)** и **RSI (14)**:  
- **Покупка** 🟢, если RSI < 30 и EMA_5 растёт.  
- **Продажа** 🔴, если RSI > 70 и EMA_5 падает.  
- Сделки совершаются только на новой свече, чтобы избежать дублирования.  

### Install  
1. ```bash
   pip install ccxt pandas ta logging
   ```
2. Set up Api keys  
3. python mts.py
