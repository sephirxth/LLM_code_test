import pygame
import math
import random
from collections import deque

# --- 配置参数 ---
# 窗口设置
WIDTH, HEIGHT = 800, 800
FPS = 60
BG_COLOR = (0, 0, 0)

# 物理常数
PPM = 100.0  # Pixels Per Meter (1米 = 100像素)
GRAVITY = 9.81 * PPM  # 重力加速度 (像素/秒^2)
RESTITUTION = 0.85    # 弹性系数 (能量保留)
FRICTION = 0.99       # 空气阻力 (防止速度无限增加)

# 容器设置
HEPTAGON_RADIUS = 300
SIDES = 7
ROTATION_SPEED = 15  # 度/秒

# 球体设置
BALL_COUNT = 20
BALL_RADIUS = 8
TRAIL_LENGTH = 100

class Ball:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        # 随机初始速度 (-5 到 5 m/s)
        self.vel = pygame.math.Vector2(random.uniform(-5, 5), random.uniform(-5, 5)) * PPM
        self.radius = BALL_RADIUS
        # 随机颜色 (避免太暗)
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        # 轨迹 (使用deque优化性能)
        self.trail = deque(maxlen=TRAIL_LENGTH)
        self.mass = 1.0 # 假设质量为1

    def update(self, dt):
        # 记录轨迹
        if len(self.trail) == 0 or (self.pos - self.trail[-1]).length_squared() > 4:
            self.trail.append(self.pos.copy())

        # 应用重力
        self.vel.y += GRAVITY * dt
        # 应用空气阻力
        self.vel *= FRICTION
        # 更新位置
        self.pos += self.vel * dt

    def draw(self, screen):
        # 绘制轨迹
        if len(self.trail) > 1:
            pygame.draw.lines(screen, self.color, False, list(self.trail), 1)
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
        # 绘制高光 (模拟3D球体效果)
        highlight_pos = (int(self.pos.x - self.radius * 0.3), int(self.pos.y - self.radius * 0.3))
        pygame.draw.circle(screen, (255, 255, 255), highlight_pos, 2)

class HeptagonContainer:
    def __init__(self, center, radius):
        self.center = pygame.math.Vector2(center)
        self.radius = radius
        self.angle = 0  # 当前旋转角度 (弧度)
        self.rotation_speed = math.radians(ROTATION_SPEED) # 转换为弧度/秒
        self.vertices = []
        self.update_vertices()

    def update(self, dt):
        # 更新旋转角度 (顺时针为正)
        self.angle += self.rotation_speed * dt
        self.update_vertices()

    def update_vertices(self):
        self.vertices = []
        for i in range(SIDES):
            # 计算每个顶点的角度：当前基础角度 + 偏移量
            theta = self.angle + i * (2 * math.pi / SIDES)
            # 极坐标转笛卡尔坐标
            x = self.center.x + self.radius * math.cos(theta)
            y = self.center.y + self.radius * math.sin(theta)
            self.vertices.append(pygame.math.Vector2(x, y))

    def draw(self, screen):
        # 绘制多边形边界
        if len(self.vertices) > 1:
            pygame.draw.polygon(screen, (200, 200, 200), self.vertices, 3)

class PhysicsEngine:
    @staticmethod
    def check_wall_collisions(balls, container):
        # 获取容器的边
        verts = container.vertices
        n = len(verts)
        
        for ball in balls:
            for i in range(n):
                p1 = verts[i]
                p2 = verts[(i + 1) % n] # 下一个顶点，闭合回路
                
                # 计算墙壁向量和法向量
                wall_vec = p2 - p1
                wall_len = wall_vec.length()
                if wall_len == 0: continue
                
                wall_unit = wall_vec / wall_len
                # 计算指向容器内部的法向量
                # 假设顶点顺时针排列，法向量应为 (-dy, dx) 或 (dy, -dx)
                # 这里我们通过指向圆心来确定正确的法向量方向
                mid_point = (p1 + p2) / 2
                to_center = container.center - mid_point
                normal = pygame.math.Vector2(-wall_unit.y, wall_unit.x)
                
                if normal.dot(to_center) < 0:
                    normal = -normal # 确保法向量指向内部

                # 计算球心到墙壁直线的距离
                # 向量 P1->Ball
                p1_to_ball = ball.pos - p1
                
                # 投影长度 (点积)
                projection = p1_to_ball.dot(wall_unit)
                
                # 判断球是否在当前线段的范围内 (不仅仅是无限延长的直线)
                closest_point = p1 + wall_unit * max(0, min(wall_len, projection))
                distance_vec = ball.pos - closest_point
                distance = distance_vec.length()

                # 碰撞检测
                if distance < ball.radius:
                    # 1. 位置修正 (防止穿模)：将球推回容器内
                    overlap = ball.radius - distance
                    # 如果距离极小，使用法向量推
                    push_dir = distance_vec.normalize() if distance > 0 else normal
                    ball.pos += push_dir * overlap

                    # 2. 速度反射计算
                    # 计算相对速度：球的速度 - 墙壁在碰撞点的线速度
                    # 墙壁碰撞点的线速度 V = omega x r (垂直于半径)
                    r_vec = closest_point - container.center
                    # 线速度方向是 r_vec 顺时针旋转90度
                    wall_vel_dir = pygame.math.Vector2(-r_vec.y, r_vec.x).normalize()
                    wall_linear_vel = wall_vel_dir * (container.rotation_speed * r_vec.length())

                    # 相对速度
                    rel_vel = ball.vel - wall_linear_vel
                    
                    # 只有当球试图飞出墙壁时才反弹 (点积 < 0)
                    if rel_vel.dot(normal) < 0:
                        # 反射公式: V_new = V_old - (1 + e) * (V_old . N) * N
                        j = -(1 + RESTITUTION) * rel_vel.dot(normal)
                        impulse = j * normal
                        ball.vel += impulse
                        
                        # 可选：稍微增加一点墙壁的切向摩擦带动效果
                        ball.vel += wall_linear_vel * 0.1

    @staticmethod
    def check_ball_collisions(balls):
        # 简单的 O(N^2) 碰撞检测，N=20时性能完全足够
        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                b1 = balls[i]
                b2 = balls[j]

                delta = b1.pos - b2.pos
                dist_sq = delta.length_squared()
                min_dist = b1.radius + b2.radius

                if dist_sq < min_dist * min_dist:
                    dist = math.sqrt(dist_sq)
                    if dist == 0: continue # 避免除以零

                    # 1. 位置修正 (各退一半)
                    overlap = min_dist - dist
                    normal = delta / dist
                    correction = normal * (overlap / 2.0)
                    b1.pos += correction
                    b2.pos -= correction

                    # 2. 动量守恒 (弹性碰撞)
                    # 相对速度
                    rel_vel = b1.vel - b2.vel
                    vel_along_normal = rel_vel.dot(normal)

                    # 只有当球相互靠近时才计算
                    if vel_along_normal < 0:
                        # 假设质量相等 m1=m2=1，简化公式
                        j = -(1 + RESTITUTION) * vel_along_normal
                        j /= 2.0 # (1/m1 + 1/m2) -> 2

                        impulse = j * normal
                        b1.vel += impulse
                        b2.vel -= impulse

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Rotating Heptagon Physics Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # 初始化对象
    container = HeptagonContainer((WIDTH/2, HEIGHT/2), HEPTAGON_RADIUS)
    balls = []

    def spawn_balls(n):
        balls.clear()
        for _ in range(n):
            # 在中心附近较小区域生成，防止初始时卡在墙里
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, HEPTAGON_RADIUS * 0.5)
            x = WIDTH/2 + math.cos(angle) * dist
            y = HEIGHT/2 + math.sin(angle) * dist
            balls.append(Ball(x, y))

    spawn_balls(BALL_COUNT)

    running = True
    paused = False

    while running:
        # 1. 计算时间步长 (秒)
        dt = clock.tick(FPS) / 1000.0 
        # 防止窗口拖动导致的大dt造成物理穿透，限制最大dt
        dt = min(dt, 0.05) 

        # 2. 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    spawn_balls(BALL_COUNT)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 鼠标点击添加新球 (Bonus)
                mx, my = pygame.mouse.get_pos()
                new_ball = Ball(mx, my)
                new_ball.vel = pygame.math.Vector2(0, 0) # 初始静止
                balls.append(new_ball)

        # 3. 更新逻辑
        if not paused:
            # 更新容器旋转
            container.update(dt)
            
            # 更新所有球
            for ball in balls:
                ball.update(dt)
            
            # 物理检测 (多次迭代以提高稳定性，此处做简单处理)
            PhysicsEngine.check_wall_collisions(balls, container)
            PhysicsEngine.check_ball_collisions(balls)

        # 4. 渲染
        screen.fill(BG_COLOR)
        
        # 绘制容器
        container.draw(screen)
        
        # 绘制球
        for ball in balls:
            ball.draw(screen)

        # 绘制UI信息 (Bonus)
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        info_text = font.render(f"Balls: {len(balls)} | Gravity: 9.81 m/s^2", True, (255, 255, 255))
        control_text = font.render("Controls: Space=Pause, R=Reset, Click=Add Ball, ESC=Quit", True, (150, 150, 150))
        
        screen.blit(fps_text, (10, 10))
        screen.blit(info_text, (10, 30))
        screen.blit(control_text, (10, HEIGHT - 30))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()