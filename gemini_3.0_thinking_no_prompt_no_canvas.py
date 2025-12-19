import pygame
import math
import random
from pygame import Vector2
from collections import deque

# --- 配置参数 ---
WIDTH, HEIGHT = 800, 800
CENTER = Vector2(WIDTH // 2, HEIGHT // 2)
FPS = 60

# 几何参数
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
BALL_COUNT = 20

# 物理参数
GRAVITY = 0.25           # 重力加速度 (像素/帧^2)
RESTITUTION = 0.85       # 弹性系数
ROT_SPEED_DEG = 15       # 旋转速度 (度/秒)
ROT_SPEED_RAD = math.radians(ROT_SPEED_DEG) / FPS  # 弧度/帧

# 颜色
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_TRAIL = (100, 100, 100)

class Ball:
    def __init__(self, id):
        self.id = id
        self.radius = BALL_RADIUS
        self.reset()
        self.color = pygame.Color(0, 0, 0)
        self.color.hsva = (random.randint(0, 360), 80, 90, 100)
        self.trail = deque(maxlen=100)  # 轨迹跟踪（Bonus）

    def reset(self):
        # 初始位置在中心附近，避免一开始就穿模
        self.pos = CENTER + Vector2(random.uniform(-50, 50), random.uniform(-50, 50))
        self.vel = Vector2(random.uniform(-5, 5), random.uniform(-5, 5))
        self.trail.clear()

    def update(self):
        self.trail.append(Vector2(self.pos))
        self.vel.y += GRAVITY  # 应用重力
        self.pos += self.vel

    def draw(self, surface):
        # 绘制轨迹 (Bonus)
        if len(self.trail) > 2:
            pygame.draw.lines(surface, self.color, False, list(self.trail), 1)
        
        # 绘制球体
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rotating Heptagon Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        
        self.angle = 0.0
        self.paused = False
        self.balls = [Ball(i) for i in range(BALL_COUNT)]

    def get_heptagon_vertices(self):
        vertices = []
        for i in range(7):
            theta = self.angle + math.radians(i * 360 / 7)
            x = CENTER.x + HEPTAGON_RADIUS * math.cos(theta)
            y = CENTER.y + HEPTAGON_RADIUS * math.sin(theta)
            vertices.append(Vector2(x, y))
        return vertices

    def handle_collisions(self):
        vertices = self.get_heptagon_vertices()
        
        # 1. 球与墙壁碰撞 (考虑旋转坐标系)
        for ball in self.balls:
            for i in range(7):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % 7]
                
                # 计算墙壁向量和法向量
                edge = p2 - p1
                edge_unit = edge.normalize()
                normal = Vector2(-edge_unit.y, edge_unit.x) # 指向圆外或圆内
                
                # 确保法线指向七边形内部
                to_center = CENTER - (p1 + p2)/2
                if normal.dot(to_center) < 0:
                    normal = -normal

                # 计算球到直线的距离
                ball_to_p1 = ball.pos - p1
                dist = ball_to_p1.dot(normal)

                if dist < ball.radius:
                    # 碰撞响应：考虑墙壁在该点的线速度
                    # 墙壁某点的线速度 v = ω × r
                    r_vector = ball.pos - CENTER
                    v_wall = Vector2(-r_vector.y, r_vector.x) * (ROT_SPEED_RAD * FPS / 1) # 简化计算
                    
                    # 转换到相对坐标系
                    v_rel = ball.vel - v_wall
                    
                    # 如果球正朝着墙壁运动
                    if v_rel.dot(normal) < 0:
                        # 反射相对速度
                        v_rel = v_rel - 2 * v_rel.dot(normal) * normal
                        # 应用弹性系数
                        ball.vel = (v_wall + v_rel) * RESTITUTION
                        # 防止穿透：修正位置
                        ball.pos += normal * (ball.radius - dist)

        # 2. 球与球碰撞 (动量守恒)
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                b1, b2 = self.balls[i], self.balls[j]
                dist_vec = b1.pos - b2.pos
                distance = dist_vec.length()
                
                if distance < (b1.radius + b2.radius):
                    if distance == 0: continue
                    normal = dist_vec.normalize()
                    
                    # 相对速度
                    rel_vel = b1.vel - b2.vel
                    vel_along_normal = rel_vel.dot(normal)
                    
                    # 只在靠近时碰撞
                    if vel_along_normal < 0:
                        # 简单的弹性碰撞 (假设质量相等)
                        impulse = (-(1 + RESTITUTION) * vel_along_normal) / 2
                        impulse_vec = impulse * normal
                        
                        b1.vel += impulse_vec
                        b2.vel -= impulse_vec
                        
                        # 防止重叠
                        overlap = (b1.radius + b2.radius) - distance
                        b1.pos += normal * (overlap / 2)
                        b2.pos -= normal * (overlap / 2)

    def run(self):
        running = True
        while running:
            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    if event.key == pygame.K_r:
                        for ball in self.balls: ball.reset()
                if event.type == pygame.MOUSEBUTTONDOWN: # Bonus: 点击添加球
                    new_ball = Ball(len(self.balls))
                    new_ball.pos = Vector2(pygame.mouse.get_pos())
                    self.balls.append(new_ball)

            if not self.paused:
                # 更新状态
                self.angle += ROT_SPEED_RAD
                for ball in self.balls:
                    ball.update()
                self.handle_collisions()

            # 渲染
            self.screen.fill(COLOR_BLACK)
            
            # 绘制七边形
            vertices = self.get_heptagon_vertices()
            pygame.draw.polygon(self.screen, COLOR_WHITE, vertices, 3)
            
            # 绘制球
            for ball in self.balls:
                ball.draw(self.screen)

            # 绘制UI (Bonus: FPS监控)
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())} | Balls: {len(self.balls)}", True, COLOR_WHITE)
            hint_text = self.font.render("Space: Pause | R: Reset | Mouse: Add Ball | ESC: Quit", True, COLOR_WHITE)
            self.screen.blit(fps_text, (10, 10))
            self.screen.blit(hint_text, (10, 35))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    sim = Simulation()
    sim.run()