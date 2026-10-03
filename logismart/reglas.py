import sys
from datetime import date, time

HORA_INICIO = time(10, 0)
HORA_FIN = time(16, 0)
DIAS_POR_VENCER = 30

# P autorizado, Q sobrepeso, R peligrosos, S certificación vigente, H en horario, W por vencer
# A = P ∧ S ∧ ¬Q, E = P ∧ (R ∨ Q), B = R ∧ ¬H, L = S ∧ W


def vf(valor):
    if valor:
        return "V"
    return "F"


def validar(premisas):
    for nombre in premisas:
        if type(premisas[nombre]) != bool:
            raise TypeError("La premisa " + nombre + " debe ser True o False")


def hora_permitida(hora, inicio=None, fin=None):
    if inicio is None:
        inicio = HORA_INICIO
    if fin is None:
        fin = HORA_FIN
    return inicio <= hora <= fin


def estado_certificacion(vence, hoy=None, dias_aviso=None):
    if hoy is None:
        hoy = date.today()
    if dias_aviso is None:
        dias_aviso = DIAS_POR_VENCER

    dias = (vence - hoy).days
    vigente = dias >= 0
    por_vencer = vigente and dias <= dias_aviso

    return vigente, por_vencer, dias


def evaluar_camion(P, Q, R, S):
    validar({"P": P, "Q": Q, "R": R, "S": S})

    acceso_estandar = P and S and (not Q)
    inspeccion_especial = P and (R or Q)

    return {"acceso_estandar": acceso_estandar, "inspeccion_especial": inspeccion_especial}


def decidir(P, Q, R, S, H=True, W=False):
    validar({"P": P, "Q": Q, "R": R, "S": S, "H": H, "W": W})

    A = P and S and (not Q)
    E = P and (R or Q)
    B = R and (not H)
    L = S and W
    acceso_final = A and (not B)

    pasos = []
    pasos.append("Premisas: P=" + vf(P) + " Q=" + vf(Q) + " R=" + vf(R) +
                 " S=" + vf(S) + " H=" + vf(H) + " W=" + vf(W))
    pasos.append("A = P ∧ S ∧ ¬Q = " + vf(P) + " ∧ " + vf(S) + " ∧ " + vf(not Q) + " = " + vf(A))
    pasos.append("E = P ∧ (R ∨ Q) = " + vf(P) + " ∧ (" + vf(R) + " ∨ " + vf(Q) + ") = " + vf(E))
    pasos.append("B = R ∧ ¬H = " + vf(R) + " ∧ " + vf(not H) + " = " + vf(B))
    pasos.append("L = S ∧ W = " + vf(S) + " ∧ " + vf(W) + " = " + vf(L))
    pasos.append("Acceso final = A ∧ ¬B = " + vf(A) + " ∧ " + vf(not B) + " = " + vf(acceso_final))

    cuantos_calculos = len(pasos)

    if not P:
        resultado = "ACCESO DENEGADO"
        semaforo = "rojo"
        pasos.append("Sin autorización previa (P=F): no puede entrar.")
    elif B:
        resultado = "BLOQUEADO POR HORARIO"
        semaforo = "rojo"
        pasos.append("Lleva materiales peligrosos fuera del horario permitido (R=V, H=F).")
    elif not S:
        resultado = "ACCESO DENEGADO"
        semaforo = "rojo"
        pasos.append("El conductor no tiene certificación vigente (S=F).")
    elif E:
        resultado = "INSPECCIÓN ESPECIAL"
        semaforo = "amarillo"
        if Q:
            pasos.append("Excede el peso (Q=V): va a inspección y no entra normal.")
        else:
            pasos.append("Lleva materiales peligrosos (R=V): entra, pero con inspección.")
    else:
        resultado = "ACCESO ESTÁNDAR"
        semaforo = "verde"
        pasos.append("Cumple todo: autorizado, certificado y sin exceso de peso.")

    if L:
        pasos.append("Aviso: la certificación del conductor vence pronto, que la renueve.")
        if semaforo == "verde":
            semaforo = "amarillo"

    return {
        "A": A,
        "E": E,
        "B": B,
        "L": L,
        "acceso_final": acceso_final,
        "resultado": resultado,
        "semaforo": semaforo,
        "pasos": pasos,
        "motivo": pasos[cuantos_calculos:],
    }


def tabla_regla_horario():
    tabla = []
    valores = [True, False]

    for R in valores:
        for H in valores:
            tabla.append({"R": R, "H": H, "no_H": not H, "B": R and (not H)})

    return tabla


def tabla_regla_vigencia():
    tabla = []
    valores = [True, False]

    for S in valores:
        for W in valores:
            # sin vigencia no puede estar por vencer
            posible = S or (not W)
            tabla.append({"S": S, "W": W, "L": S and W, "posible": posible})

    return tabla


def tabla_completa():
    tabla = []
    valores = [True, False]

    for P in valores:
        for Q in valores:
            for R in valores:
                for S in valores:
                    for H in valores:
                        for W in valores:
                            d = decidir(P, Q, R, S, H, W)
                            tabla.append({
                                "P": P, "Q": Q, "R": R, "S": S, "H": H, "W": W,
                                "A": d["A"], "E": d["E"], "B": d["B"], "L": d["L"],
                                "acceso_final": d["acceso_final"],
                                "resultado": d["resultado"],
                            })

    return tabla


def imprimir_tablas():
    print("Regla 3: B = R ∧ ¬H")
    print(" R  H  ¬H | B")
    for fila in tabla_regla_horario():
        print(" " + vf(fila["R"]) + "  " + vf(fila["H"]) + "  " + vf(fila["no_H"]) + "  | " + vf(fila["B"]))

    print("\nRegla 4: L = S ∧ W")
    print(" S  W | L")
    for fila in tabla_regla_vigencia():
        linea = " " + vf(fila["S"]) + "  " + vf(fila["W"]) + " | " + vf(fila["L"])
        if not fila["posible"]:
            linea = linea + "   (imposible: no puede estar por vencer sin estar vigente)"
        print(linea)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    imprimir_tablas()
