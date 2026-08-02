import random
import numpy as np

class CloudKitchenVRPSA:
    def __init__(self, num_orders, num_vehicles, distance_matrix, time_windows, pop_size=50, generations=100, mutation_rate=0.1):
        """
        حل مسئله مسیریابی پیک‌های موتوری کترینگ با الگوریتم ژنتیک جهت حفظ کیفیت و گرم ماندن غذا
        """
        self.num_orders = num_orders
        self.num_vehicles = num_vehicles
        self.distance_matrix = distance_matrix
        self.time_windows = time_windows # حداکثر زمان مجاز تحویل (دقیقه) برای گرم ماندن غذا
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_rate = mutation_rate

    def create_individual(self):
        # ساخت کروموزوم: جایگشتی از شماره سفارش‌ها
        chromosome = list(range(1, self.num_orders + 1))
        random.shuffle(chromosome)
        return chromosome

    def calculate_fitness(self, individual):
        """محاسبه مسافت طی‌شده + جریمه سنگین برای تاخیر در تحویل (سرد شدن غذا)"""
        total_distance = 0
        penalty = 0
        
        # تقسیم سفارش‌ها بین پیک‌های موجود
        routes = np.array_split(individual, self.num_vehicles)
        
        for route in routes:
            last_node = 0  # 0 یعنی آشپزخانه مرکزی
            route_time = 0
            
            for order in route:
                dist = self.distance_matrix[last_node][order]
                total_distance += dist
                route_time += dist * 2  # فرض: هر کیلومتر ۲ دقیقه طول می‌کشد
                
                # قید گرم ماندن غذا: اگر از زمان مجاز بگذرد، جریمه ثبت می‌شود
                max_allowed_time = self.time_windows.get(order, 45)
                if route_time > max_allowed_time:
                    penalty += (route_time - max_allowed_time) * 100 # جریمه سنگین برای افت کیفیت غذا
                
                last_node = order
            
            # بازگشت پیک به آشپزخانه
            total_distance += self.distance_matrix[last_node][0]
            
        total_cost = total_distance + penalty
        # برازندگی بیشتر یعنی هزینه و تاخیر کمتر
        fitness = 1 / (total_cost + 1e-6)
        return fitness, total_cost

    def crossover(self, parent1, parent2):
        """اپراتور تقاطع Order Crossover (OX) برای جلوگیری از تکرار سفارش"""
        size = len(parent1)
        if size < 2:
            return parent1[:]
            
        start, end = sorted(random.sample(range(size), 2))
        child = [None] * size
        child[start:end] = parent1[start:end]
        
        pointer = end
        for gene in parent2[end:] + parent2[:end]:
            if gene not in child:
                if pointer >= size:
                    pointer = 0
                child[pointer] = gene
                pointer += 1
        return child

    def mutate(self, individual):
        """اپراتور جهش Swap (جابه‌جایی دو سفارش)"""
        if random.random() < self.mutation_rate and len(individual) > 1:
            idx1, idx2 = random.sample(range(len(individual)), 2)
            individual[idx1], individual[idx2] = individual[idx2], individual[idx1]
        return individual

    def solve(self):
        # ساخت جمعیت اولیه
        population = [self.create_individual() for _ in range(self.pop_size)]
        best_history = []
        best_individual = None
        min_cost = float('inf')

        for gen in range(self.generations):
            fitness_scores = [self.calculate_fitness(ind) for ind in population]
            
            for i, (fit, cost) in enumerate(fitness_scores):
                if cost < min_cost:
                    min_cost = cost
                    best_individual = population[i]

            best_history.append(min_cost)

            # انتخاب والدین با روش تورنمنت (Tournament Selection)
            selected_parents = []
            for _ in range(self.pop_size):
                tournament = random.sample(population, min(3, len(population)))
                best_t = max(tournament, key=lambda ind: self.calculate_fitness(ind)[0])
                selected_parents.append(best_t)

            # تولید نسل جدید
            new_population = []
            for i in range(0, self.pop_size, 2):
                p1 = selected_parents[i]
                p2 = selected_parents[(i+1) % self.pop_size]
                c1 = self.mutate(self.crossover(p1, p2))
                c2 = self.mutate(self.crossover(p2, p1))
                new_population.extend([c1, c2])

            population = new_population

        # تفکیک مسیر نهایی پیک‌ها
        best_routes = [list(r) for r in np.array_split(best_individual, self.num_vehicles)]
        
        return {
            "best_routes": best_routes,
            "min_total_cost": min_cost,
            "convergence_curve": best_history
        }