import math
from pyomo.environ import *

"""
##-------------------------
ici on minimise A0 et l'on maximise la perte à la fin 
(permet la meilleur optimisation ainsi que une petite marge)
ainsi on gagne une dose sur le planing de julien 

##-------------------------
"""
patients = {
    1: {"weight": 65},
    2: {"weight": 62},
    3: {"weight": 63},
    4: {"weight": 64},
    5: {"weight": 65},
    6: {"weight": 70},
    7: {"weight": 80},
    8: {"weight": 100},
    9: {"weight": 81},
    10: {"weight": 55},
    11: {"weight": 100},
    12 : {"weight": 59},
}

alpha = 2.0          # MBq/kg
slot_duration = 20  # minutes

K = 30               # nb de slots dispo (>= N)
start_time = 8 * 60  # 08:00
slots = [start_time + k * slot_duration for k in range(K)]

delivery_time = 8*60  # 08:00

#donnée relative au traceur utilisé 
half_life = 110
lam = math.log(2) / half_life
delta = math.exp(-lam * slot_duration)

# doses
D = {i: alpha * patients[i]["weight"] for i in patients}
P_list = list(patients.keys())
N = len(P_list)
if N > K:
    raise ValueError("Il faut K >= N (nb patients).")

# -------------------------
# Modèle builder
# -------------------------
def build_model():
    m = ConcreteModel()
    m.P = Set(initialize=P_list)
    m.K = RangeSet(0, K - 1)

    # ---- variable de commande : A0 = 400 * q ----
    m.q = Var(domain=NonNegativeIntegers)   # nb de 'doses de 400MBq'
    m.A0 = Expression(expr=400 * m.q)

    # décisions de planning
    m.x = Var(m.P, m.K, domain=Binary)
    m.y = Var(m.P, m.K, domain=NonNegativeReals)
    m.u = Var(m.K, domain=Binary)

    # stock avant injection
    m.S = Var(m.K, domain=NonNegativeReals)

    # stock initial au slot 0 (déjà décroît depuis livraison)
    # S0 = A0 * exp(-lam*(slots[0] - delivery_time))
    decay_to_first = math.exp(-lam * (slots[0] - delivery_time))
    m.c_init = Constraint(expr=m.S[0] == m.A0 * decay_to_first)

    # 1 patient par slot si slot utilisé
    def one_patient_per_slot(m, k):
        return sum(m.x[i, k] for i in m.P) == m.u[k]
    m.c1 = Constraint(m.K, rule=one_patient_per_slot)

    # chaque patient exactement une fois
    def one_slot_per_patient(m, i):
        return sum(m.x[i, k] for k in m.K) == 1
    m.c2 = Constraint(m.P, rule=one_slot_per_patient)

    # dose fixe par patient
    def dose_constraint(m, i):
        return sum(m.y[i, k] for k in m.K) == D[i]
    m.c3 = Constraint(m.P, rule=dose_constraint)

    # lien y <= D_i * x
    def linking(m, i, k):
        return m.y[i, k] <= D[i] * m.x[i, k]
    m.c4 = Constraint(m.P, m.K, rule=linking)

    # pas consommer plus que stock dispo
    def cannot_use_more_than_stock(m, k):
        return sum(m.y[i, k] for i in m.P) <= m.S[k]
    m.c5 = Constraint(m.K, rule=cannot_use_more_than_stock)

    # dynamique correcte : on enlève, puis décroissance
    def stock_flow(m, k):
        if k == K - 1:
            return Constraint.Skip
        used_k = sum(m.y[i, k] for i in m.P)
        return m.S[k + 1] == (m.S[k] - used_k) * delta
    m.c6 = Constraint(m.K, rule=stock_flow)

    # exactement N slots utilisés
    m.c7 = Constraint(expr=sum(m.u[k] for k in m.K) == N)

    # pas de trous

    def no_gaps(m, k):
        if k == 0:
            return Constraint.Skip
        return m.u[k] <= m.u[k - 1]
    m.c8 = Constraint(m.K, rule=no_gaps)

    # dernier slot utilisé = N-1
    m.last_k = N - 1

    # expression stock juste après le dernier patient
    m.used_last = Expression(expr=sum(m.y[i, m.last_k] for i in m.P))
    m.stock_after_last = Expression(expr=m.S[m.last_k] - m.used_last)

    return m

# -------------------------
# Solveurs
# -------------------------
solver = SolverFactory("cbc")  # ou "glpk"

# -------------------------
# Étape 1 : minimiser la commande (q)
# -------------------------
m1 = build_model()
m1.obj = Objective(expr=m1.q, sense=minimize)
solver.solve(m1, tee=True)

q_star = int(round(value(m1.q)))
A0_star = 400 * q_star

print("\n=== Étape 1 (commande minimale) ===")
print("q* =", q_star, "-> A0* =", A0_star, "MBq")

# -------------------------
# Étape 2 : à A0 fixé minimal, maximiser le stock après dernier patient
# -------------------------
m2 = build_model()
m2.fix_q = Constraint(expr=m2.q == q_star)
m2.obj = Objective(expr=m2.stock_after_last, sense=maximize)
solver.solve(m2, tee=True)

# -------------------------
# Affichage final
# -------------------------
def fmt_time(minutes):
    return f"{minutes//60:02d}:{minutes%60:02d}"

print("\n=== Solution finale ===")
print("A0 commandé :", A0_star, "MBq (", q_star, "x 400 )")
print("Stock juste après dernier patient :", value(m2.stock_after_last))


print("\nPlanning injections :")
for k in range(K):
    if value(m2.u[k]) > 0.5:
        for i in m2.P:
            if value(m2.x[i, k]) > 0.5:
                print(f"slot {k:02d} {fmt_time(slots[k])} patient {i} dose={value(m2.y[i,k]):.1f} MBq stock_avant={value(m2.S[k]):.1f}")
                break
