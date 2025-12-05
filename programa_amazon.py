import time
import re
import matplotlib.pyplot as plt
import numpy as np
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

def limpiar_nombre_producto(nombre):
    """Limpia el nombre del producto de texto innecesario"""
    if not nombre:
        return "Producto sin nombre"
    
    patrones_a_eliminar = [
        r'Opciones:\s*\d+\s*tamaños?\s*\d+\s*tamaños?',
        r'\d+\.\d+\s*de 5 estrellas',
        r'\d+[k]?\s*comprados?',
        r'Precio,\s*página del producto',
        r'Precio\s*anterior:',
        r'Precio de lista:',
        r'Entrega\s*GRATIS.*',
        r'Sólo queda\(n\).*',
        r'Ver opciones',
        r'Más opciones de compra',
        r'\(\d+ ofertas nuevas y de caja abierta\)',
        r'Patrocinado',
        r'\+(\d+)\s*otro(s)?\s*color(es)?/?patrón(es)?',
        r'Más vendidoen.*',
        r'\$\d+[,.]\d+',
        r'\d+\s*de\s*\d+\s*estrellas',
    ]
    
    nombre_limpio = nombre
    for patron in patrones_a_eliminar:
        nombre_limpio = re.sub(patron, '', nombre_limpio, flags=re.IGNORECASE)
    
    nombre_limpio = ' '.join(nombre_limpio.split())
    
    if len(nombre_limpio.strip()) < 10:
        partes = nombre.split()
        nombre_limpio = ' '.join(partes[:10]) if len(partes) > 10 else nombre
        nombre_limpio = ' '.join(nombre_limpio.split())
    
    return nombre_limpio.strip()

def configurar_driver():
    """Configura el driver de Chrome para Selenium"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        rutas_chrome = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
        ]
        
        for ruta in rutas_chrome:
            if os.path.exists(ruta):
                chrome_options.binary_location = ruta
                break
        
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        print(f"Error configurando Chrome: {str(e)}")
        return None

def buscar_productos_amazon(producto, cantidad):
    """Busca productos en Amazon México y extrae nombre y precio"""
    driver = configurar_driver()
    if not driver:
        return []
    
    productos_data = []
    
    try:
        print("\nConectando a Amazon México...")
        driver.get("https://www.amazon.com.mx")
        time.sleep(3)
        
        try:
            cookie_button = driver.find_element(By.ID, "sp-cc-accept")
            cookie_button.click()
            time.sleep(1)
        except:
            pass
        
        print(f"Buscando: '{producto}'")
        try:
            search_box = driver.find_element(By.ID, "twotabsearchtextbox")
            search_box.clear()
            search_box.send_keys(producto)
            search_box.send_keys(Keys.RETURN)
            time.sleep(4)
        except:
            producto_url = producto.replace(" ", "+")
            driver.get(f"https://www.amazon.com.mx/s?k={producto_url}")
            time.sleep(4)
        
        print("Cargando productos...")
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1)
        
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        productos = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        if len(productos) < 5:
            productos = soup.find_all('div', class_='s-result-item')
        
        if len(productos) < 5:
            productos = soup.find_all('div', {'data-asin': True})
            productos = [p for p in productos if p.get('data-asin', '') != '']
        
        print(f"Encontrados {len(productos)} productos totales")
        
        for i, prod in enumerate(productos):
            if len(productos_data) >= cantidad:
                break
                
            try:
                nombre = None
                h2_tag = prod.find('h2')
                if h2_tag:
                    span_tag = h2_tag.find('span')
                    if span_tag and span_tag.text.strip():
                        nombre = span_tag.text.strip()
                
                if not nombre:
                    span_tags = prod.find_all('span', class_=True)
                    for span in span_tags:
                        classes = span.get('class', [])
                        if any('text-normal' in cls or 'size-base' in cls or 'color-base' in cls for cls in classes):
                            if span.text.strip() and len(span.text.strip()) > 10:
                                nombre = span.text.strip()
                                break
                
                if not nombre:
                    all_texts = prod.find_all(text=True)
                    for text in all_texts:
                        text_str = text.strip()
                        if len(text_str) > 20 and '$' not in text_str and not text_str.isdigit():
                            nombre = text_str
                            break
                
                if not nombre:
                    continue
                
                nombre_limpio = limpiar_nombre_producto(nombre)
                precio = None
                precio_spans = prod.find_all('span', class_=['a-price-whole', 'a-offscreen', 'a-price'])
                
                for span in precio_spans:
                    precio_texto = span.text.strip()
                    if '$' in precio_texto:
                        precio_texto = precio_texto.replace('$', '').replace(',', '').replace('MXN', '').strip()
                        
                        if ' ' in precio_texto:
                            precio_texto = precio_texto.split()[0]
                        if '-' in precio_texto:
                            precio_texto = precio_texto.split('-')[0]
                        
                        try:
                            if '.' in precio_texto:
                                parts = precio_texto.split('.')
                                if len(parts) > 2:
                                    precio_texto = parts[0] + '.' + parts[1]
                            precio = float(precio_texto)
                            break
                        except:
                            continue
                
                if precio and nombre_limpio:
                    nombre_corto = (nombre_limpio[:35] + '...') if len(nombre_limpio) > 35 else nombre_limpio
                    
                    productos_data.append({
                        'Nombre': nombre_corto,
                        'Precio': precio,
                        'Nombre_Completo': nombre_limpio,
                        'Nombre_Original': nombre
                    })
                    
                    print(f"  {len(productos_data)}. {nombre_corto}")
                    print(f"     Precio: ${precio:.2f} MXN")
                    
            except:
                continue
        
        driver.quit()
        return productos_data
        
    except Exception as e:
        print(f"Error en la búsqueda: {str(e)}")
        if driver:
            driver.quit()
        return []

def crear_grafica_y_lista(productos, umbral, cantidad_solicitada):
    """Crea gráfica de barras y muestra lista de productos por debajo del umbral"""
    if not productos:
        print("No hay datos para graficar")
        return
    
    print(f"\n" + "="*60)
    print(f"RESULTADOS: {len(productos)} de {cantidad_solicitada} productos encontrados")
    print("="*60)
    
    if len(productos) > cantidad_solicitada:
        productos = productos[:cantidad_solicitada]
    
    productos_debajo_umbral = [p for p in productos if p['Precio'] <= umbral]
    
    if productos_debajo_umbral:
        print(f"\nPRODUCTOS POR DEBAJO DEL UMBRAL (${umbral:.2f}):")
        print("-"*50)
        for i, prod in enumerate(productos_debajo_umbral, 1):
            ahorro = umbral - prod['Precio']
            
            print(f"{i:2d}. {prod['Nombre_Completo']}")
            print(f"    Precio: ${prod['Precio']:.2f} MXN")
            print(f"    Ahorro: ${ahorro:.2f}")
            print()
    else:
        print(f"\nNo hay productos por debajo del umbral de ${umbral:.2f}")
    
    nombres = [p['Nombre'] for p in productos]
    precios = [p['Precio'] for p in productos]
    indices = range(len(productos))
    
    colores = []
    for precio in precios:
        if precio <= umbral:
            colores.append('#2ecc71')
        else:
            colores.append('#e74c3c')
    
    plt.figure(figsize=(14, 8))
    barras = plt.bar(indices, precios, color=colores, alpha=0.8, edgecolor='black', width=0.7)
    
    plt.axhline(y=umbral, color='red', linestyle='--', linewidth=2.5, 
                label=f'Umbral: ${umbral:.2f}', alpha=0.7)
    
    plt.xlabel('Productos')
    plt.ylabel('Precio ($ MXN)')
    plt.title(f'Comparación de {len(productos)} Productos - Umbral: ${umbral:.2f}')
    
    plt.xticks(indices, [f"Prod {i+1}" for i in indices], rotation=0, fontsize=10)
    
    for i, nombre in enumerate(nombres):
        plt.text(i, -max(precios)*0.05, nombre[:20] + '...' if len(nombre) > 20 else nombre, 
                ha='center', va='top', rotation=45, fontsize=8)
    
    for i, (barra, precio) in enumerate(zip(barras, precios)):
        altura = barra.get_height()
        plt.text(barra.get_x() + barra.get_width()/2, altura + max(precios)*0.01,
                f'${precio:.2f}', ha='center', va='bottom', fontsize=10,
                fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    plt.ylim(0, max(precios) * 1.15)
    plt.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    from matplotlib.patches import Patch
    leyenda_elementos = [
        Patch(facecolor='#2ecc71', label='Por debajo del umbral'),
        Patch(facecolor='#e74c3c', label='Por encima del umbral')
    ]
    plt.legend(handles=leyenda_elementos, loc='upper right')
    
    plt.tight_layout()
    
    print("\nGenerando gráfica...")
    plt.show()
    
    print(f"\n" + "="*60)
    print("RESUMEN FINAL:")
    print("="*60)
    print(f"Productos solicitados: {cantidad_solicitada}")
    print(f"Productos encontrados: {len(productos)}")
    print(f"Productos por debajo del umbral: {len(productos_debajo_umbral)}")
    
    if productos_debajo_umbral:
        print(f"\nMEJORES OPCIONES (más económicas):")
        productos_ordenados = sorted(productos_debajo_umbral, key=lambda x: x['Precio'])
        for i, prod in enumerate(productos_ordenados[:3], 1):
            print(f"{i}. {prod['Nombre_Completo']}")
            print(f"   ${prod['Precio']:.2f} (Ahorro: ${umbral - prod['Precio']:.2f})")
            print()

def main():
    """Función principal"""
    print("="*60)
    print("COMPARADOR DE PRECIOS - AMAZON MÉXICO")
    print("="*60)
    
    print("\nIngresa el nombre del producto: ", end="")
    producto = input().strip()
    
    if not producto:
        print("Debes ingresar un producto")
        return
    
    while True:
        try:
            print("Cantidad de productos a comparar (1-20): ", end="")
            cantidad = int(input())
            if 1 <= cantidad <= 20:
                break
            print("Ingresa un número entre 1 y 20")
        except:
            print("Ingresa un número válido")
    
    while True:
        try:
            print("Umbral de precio máximo (MXN): $", end="")
            umbral = float(input())
            if umbral > 0:
                break
            print("El precio debe ser mayor a 0")
        except:
            print("Ingresa un número válido")
    
    print("\n" + "-"*60)
    print("Buscando productos...")
    
    productos = buscar_productos_amazon(producto, cantidad)
    
    if productos:
        crear_grafica_y_lista(productos, umbral, cantidad)
    else:
        print("\nNo se pudieron obtener productos.")
        print("\nRecomendaciones:")
        print("  - Verifica tu conexión a internet")
        print("  - Intenta con otro término de búsqueda")
        print("  - Asegúrate de tener Chrome instalado")
    
    print("\n" + "="*60)
    print("Programa finalizado")
    print("="*60)

if __name__ == "__main__":
    main()