# ========================================
# SHADOW DEAL - ЯНДЕКС.МАРКЕТ
# ========================================
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Shadow Deal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family: 'Segoe UI', Arial; }
            body { background: linear-gradient(135deg, #0a0015, #1a0a2e); min-height:100vh; color:#fff; padding:20px; }
            .container { max-width:650px; margin:0 auto; }
            .header { text-align:center; padding:40px 0 20px; }
            .header h1 { font-size:52px; background:linear-gradient(135deg,#c084fc,#e879f9); -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:800; }
            .header p { color:#a78bfa; font-size:14px; margin-top:8px; }
            .search-card { background:rgba(20,10,40,0.6); border:1px solid rgba(155,89,182,0.25); border-radius:20px; padding:25px; margin:20px 0; }
            .search-row { display:flex; gap:10px; }
            .search-row input { flex:1; padding:16px 20px; border-radius:15px; border:1px solid rgba(155,89,182,0.4); background:rgba(15,10,30,0.8); color:#fff; font-size:16px; outline:none; }
            .search-row input:focus { border-color:#a855f7; }
            .search-row input::placeholder { color:#6b7280; }
            .search-row button { padding:16px 30px; border-radius:15px; border:none; background:linear-gradient(135deg,#7c3aed,#a855f7); color:#fff; font-size:16px; font-weight:bold; cursor:pointer; }
            .search-row button:hover { background:linear-gradient(135deg,#6d28d9,#9333ea); }
            .loading { text-align:center; padding:40px; color:#a855f7; display:none; }
            .result { background:rgba(20,10,40,0.6); border:1px solid rgba(155,89,182,0.3); border-radius:20px; padding:30px; margin:20px 0; display:none; }
            .platform { display:inline-block; padding:7px 18px; border-radius:20px; font-size:13px; font-weight:bold; margin-bottom:18px; background:rgba(168,85,247,0.15); color:#c084fc; border:1px solid rgba(168,85,247,0.3); }
            .result img { width:100%; max-height:350px; object-fit:contain; border-radius:15px; background:rgba(255,255,255,0.03); margin-bottom:20px; }
            .result h2 { color:#e9d5ff; font-size:18px; margin-bottom:15px; }
            .price-now { font-size:48px; font-weight:800; color:#4ade80; }
            .price-old { text-decoration:line-through; color:#6b7280; font-size:22px; margin-left:12px; }
            .discount { display:inline-block; background:rgba(239,68,68,0.15); color:#fca5a5; padding:5px 12px; border-radius:8px; font-size:14px; font-weight:bold; margin-left:8px; }
            .stats { display:flex; gap:30px; margin:20px 0; padding:15px 20px; background:rgba(168,85,247,0.05); border-radius:12px; }
            .stat { text-align:center; }
            .stat .val { font-size:22px; font-weight:bold; color:#c084fc; }
            .stat .lbl { font-size:11px; color:#6b7280; margin-top:3px; }
            .buy-btn { display:block; text-align:center; padding:16px; background:linear-gradient(135deg,#7c3aed,#a855f7); color:#fff; text-decoration:none; border-radius:12px; font-weight:bold; font-size:18px; margin-top:20px; }
            .buy-btn:hover { background:linear-gradient(135deg,#6d28d9,#9333ea); }
            .footer { text-align:center; padding:30px 0; color:#6b7280; font-size:12px; }
            .footer a { color:#a855f7; text-decoration:none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🟣 Shadow Deal</h1>
                <p>Лучшая цена на Яндекс.Маркет</p>
            </div>
            <div class="search-card">
                <div class="search-row">
                    <input type="text" id="query" placeholder="iPhone 15, наушники..." value="iPhone 15" autofocus>
                    <button onclick="findDeal()">🔍 Найти</button>
                </div>
            </div>
            <div class="loading" id="loading">Ищем лучшую цену...</div>
            <div class="result" id="result"></div>
            <div class="footer">Shadow Deal © 2026 | <a href="https://t.me/kmyfg" target="_blank">@kmyfg</a></div>
        </div>
        <script>
            function findDeal() {
                const q = document.getElementById('query').value.trim();
                if (!q) return;
                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                fetch('/api/deal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:q})})
                .then(r => r.json())
                .then(d => {
                    document.getElementById('loading').style.display = 'none';
                    if (d.error) { alert(d.error); return; }
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerHTML = `
                        <span class="platform">🛍 ${d.marketplace}</span>
                        <img src="${d.image}" onerror="this.style.display='none'">
                        <h2>${d.title}</h2>
                        <div style="margin:20px 0">
                            <span class="price-now">${d.price.toLocaleString()} ₽</span>
                            ${d.old_price ? `<span class="price-old">${d.old_price.toLocaleString()} ₽</span><span class="discount">-${d.discount}%</span>` : ''}
                        </div>
                        <a href="${d.url}" target="_blank" class="buy-btn">Перейти к товару →</a>
                    `;
                })
                .catch(e => { document.getElementById('loading').style.display = 'none'; alert('Ошибка'); });
            }
            findDeal();
            document.getElementById('query').addEventListener('keypress', e => { if(e.key==='Enter') findDeal(); });
        </script>
    </body>
    </html>
    '''

@app.route('/api/deal', methods=['POST'])
def best_price():
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': 'Введите запрос'})
    
    # Парсим Яндекс.Маркет
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        
        # Поиск на Яндекс.Маркете
        r = requests.get(
            f'https://market.yandex.ru/search?text={query}&cvredirect=0',
            headers=headers,
            timeout=15
        )
        
        if r.status_code == 200:
            html = r.text
            
            # Ищем данные в HTML
            import re
            
            # Ищем JSON с товарами
            products_data = re.findall(r'"products":\s*(\[.*?\])', html, re.DOTALL)
            
            if products_data:
                try:
                    products = json.loads(products_data[0])
                    
                    if products:
                        # Берём первый товар
                        best = products[0]
                        
                        price = int(best.get('price', {}).get('value', 0))
                        old_price = int(best.get('price', {}).get('oldValue', 0))
                        
                        return jsonify({
                            'title': best.get('title', 'Без названия'),
                            'price': price,
                            'old_price': old_price if old_price > price else None,
                            'discount': round((1 - price / old_price) * 100) if old_price > price else 0,
                            'rating': float(best.get('rating', 0)),
                            'reviews': int(best.get('reviewCount', 0)),
                            'image': best.get('pictures', [{}])[0].get('url', '') if best.get('pictures') else '',
                            'url': f"https://market.yandex.ru{best.get('url', '')}",
                            'marketplace': 'Яндекс.Маркет'
                        })
                except:
                    pass
            
            # Если JSON не нашли - ищем обычные данные
            titles = re.findall(r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h3>', html, re.DOTALL)
            prices = re.findall(r'<span[^>]*class="[^"]*price[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
            
            if titles and prices:
                return jsonify({
                    'title': re.sub(r'<.*?>', '', titles[0]).strip()[:100],
                    'price': int(re.sub(r'\D', '', prices[0])),
                    'old_price': None,
                    'discount': 0,
                    'rating': 0,
                    'reviews': 0,
                    'image': '',
                    'url': f'https://market.yandex.ru/search?text={query}',
                    'marketplace': 'Яндекс.Маркет'
                })
                
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)[:100]}'})
    
    return jsonify({'error': 'Ничего не найдено'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
