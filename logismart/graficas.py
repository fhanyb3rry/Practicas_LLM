import riesgos

FONDO = "#1b0d3a"
TEXTO = "#c9f7ee"
CELDAS = {"bajo": "#1d4d35", "medio": "#5c5220", "alto": "#6b4220", "crítico": "#6b2030"}


def mezclar(color, fondo, cantidad):
    # cantidad 0 = puro fondo, 1 = puro color
    nuevo = "#"
    for pos in (1, 3, 5):
        a = int(color[pos:pos + 2], 16)
        b = int(fondo[pos:pos + 2], 16)
        nuevo += format(int(b + (a - b) * cantidad), "02x")
    return nuevo


def tamano(canvas):
    ancho = canvas.winfo_width()
    alto = canvas.winfo_height()
    if ancho < 50:
        ancho = int(canvas["width"])
    if alto < 50:
        alto = int(canvas["height"])
    return ancho, alto


def dibujar_matriz(canvas, lista):
    canvas.delete("all")
    ancho, alto = tamano(canvas)

    izq, der, arriba, abajo = 48, 15, 32, 38
    celda = min((ancho - izq - der) / 5, (alto - arriba - abajo) / 5)

    canvas.create_text(izq, 14, text="Matriz de riesgos", anchor="w", fill=TEXTO, font=("Segoe UI", 11, "bold"))
    canvas.create_text(ancho - der, 14, text="●  antes     ○  después de mitigar", anchor="e",
                       fill=TEXTO, font=("Segoe UI", 8))

    for p in range(1, 6):
        for i in range(1, 6):
            x0 = izq + (p - 1) * celda
            y0 = alto - abajo - i * celda
            canvas.create_rectangle(x0, y0, x0 + celda, y0 + celda,
                                    fill=CELDAS[riesgos.nivel(p * i)], outline=FONDO)

    for numero in range(1, 6):
        canvas.create_text(izq + (numero - 0.5) * celda, alto - abajo + 12, text=str(numero), fill=TEXTO)
        canvas.create_text(izq - 12, alto - abajo - (numero - 0.5) * celda, text=str(numero), fill=TEXTO)
    canvas.create_text(izq + 2.5 * celda, alto - 8, text="Probabilidad", fill=TEXTO, font=("Segoe UI", 9))
    canvas.create_text(12, alto - abajo - 2.5 * celda, text="Impacto", fill=TEXTO, angle=90, font=("Segoe UI", 9))

    if len(lista) == 0:
        canvas.create_text(ancho / 2, alto / 2, text="Sin riesgos todavía", fill=TEXTO)
        return

    # cuántos van en cada casilla, para no encimarlos
    en_casilla = {}
    radio = min(11, celda / 3)

    def centro(p, i, posicion, cuantos):
        cx = izq + (p - 0.5) * celda + (posicion - (cuantos - 1) / 2) * radio * 1.7
        cy = alto - abajo - (i - 0.5) * celda
        return cx, cy

    cuantos_antes = {}
    cuantos_despues = {}
    for r in lista:
        casilla = (r["probabilidad"], r["impacto"])
        cuantos_antes[casilla] = cuantos_antes.get(casilla, 0) + 1
        casilla = (r["prob_residual"], r["impacto_residual"])
        cuantos_despues[casilla] = cuantos_despues.get(casilla, 0) + 1

    puestos_antes = {}
    puestos_despues = {}
    puntos = []
    for numero, r in enumerate(lista, start=1):
        a = (r["probabilidad"], r["impacto"])
        d = (r["prob_residual"], r["impacto_residual"])
        pos_a = puestos_antes.get(a, 0)
        pos_d = puestos_despues.get(d, 0)
        puestos_antes[a] = pos_a + 1
        puestos_despues[d] = pos_d + 1
        puntos.append((numero, r, centro(a[0], a[1], pos_a, cuantos_antes[a]),
                       centro(d[0], d[1], pos_d, cuantos_despues[d])))

    for numero, r, origen, destino in puntos:
        if origen != destino:
            canvas.create_line(origen[0], origen[1], destino[0], destino[1], fill="#e8e8f0",
                               dash=(3, 3), arrow="last", width=1)

    for numero, r, origen, destino in puntos:
        color = riesgos.COLORES[riesgos.nivel(r["puntaje"])]
        canvas.create_oval(origen[0] - radio, origen[1] - radio, origen[0] + radio, origen[1] + radio,
                           fill=color, outline="white")
        canvas.create_text(origen[0], origen[1], text=str(numero), fill="black", font=("Segoe UI", 8, "bold"))

        if origen != destino:
            color = riesgos.COLORES[riesgos.nivel(r["puntaje_residual"])]
            canvas.create_oval(destino[0] - radio, destino[1] - radio, destino[0] + radio, destino[1] + radio,
                               fill=CELDAS[riesgos.nivel(r["impacto_residual"] * r["prob_residual"])],
                               outline=color, width=2)
            canvas.create_text(destino[0], destino[1], text=str(numero), fill=color, font=("Segoe UI", 8, "bold"))


def dibujar_barras(canvas, lista):
    canvas.delete("all")
    ancho, alto = tamano(canvas)

    canvas.create_text(10, 14, text="Puntaje antes y después de mitigar", anchor="w", fill=TEXTO,
                       font=("Segoe UI", 11, "bold"))

    if len(lista) == 0:
        canvas.create_text(ancho / 2, alto / 2, text="Sin riesgos todavía", fill=TEXTO)
        return

    izq, der, arriba, abajo = 180, 40, 32, 10
    fila = (alto - arriba - abajo) / len(lista)
    if fila > 44:
        fila = 44
    grosor = max(fila * 0.34, 4)
    escala = (ancho - izq - der) / 25

    for numero, r in enumerate(lista, start=1):
        y = arriba + (numero - 1) * fila
        texto = str(numero) + ". " + r["modulo"]
        if len(texto) > 26:
            texto = texto[:25] + "…"
        canvas.create_text(izq - 8, y + fila / 2, text=texto, anchor="e", fill=TEXTO, font=("Segoe UI", 8))

        color_antes = riesgos.COLORES[riesgos.nivel(r["puntaje"])]
        color_despues = riesgos.COLORES[riesgos.nivel(r["puntaje_residual"])]

        y1 = y + fila / 2 - grosor - 1
        canvas.create_rectangle(izq, y1, izq + r["puntaje"] * escala, y1 + grosor, fill=color_antes, outline="")
        canvas.create_text(izq + r["puntaje"] * escala + 5, y1 + grosor / 2, text=str(r["puntaje"]),
                           anchor="w", fill=TEXTO, font=("Segoe UI", 8))

        y2 = y + fila / 2 + 1
        canvas.create_rectangle(izq, y2, izq + r["puntaje_residual"] * escala, y2 + grosor,
                                fill=mezclar(color_despues, FONDO, 0.55), outline=color_despues)
        canvas.create_text(izq + r["puntaje_residual"] * escala + 5, y2 + grosor / 2,
                           text=str(r["puntaje_residual"]), anchor="w", fill=TEXTO, font=("Segoe UI", 8))

    canvas.create_line(izq, arriba - 4, izq, alto - abajo, fill=TEXTO)
    canvas.create_text(ancho - 10, 14, text="■ antes   ▢ después", anchor="e", fill=TEXTO, font=("Segoe UI", 8))
