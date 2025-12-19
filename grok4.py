import pygame
import math
import random
import sys
import numpy as np  # 用于向量计算

# 初始化Pygame
pygame.init()

# 窗口设置
WIDTH, HEIGHT = 800, 800
CENTER = (WIDTH // 2, HEIGHT // 2)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rotating Heptagon with Bouncing Balls")
clock = pygame.time.Clock()
FPS = 60

# 常量
RADIUS = 300  # 七边形半径
BALL_RADIUS = 8
NUM_BALLS = 20
GRAVITY = 9.81 / FPS  # 调整为每帧加速度 (m/s² -> pixels/frame², 假设1像素=1m简化)
ELASTICITY = 0.85
ROTATION_SPEED = 15 / FPS  # 度/秒 -> 度/帧 (顺时针)

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

class Heptagon:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius
        self.angle = 0  # 当前旋转角度

    def update(self):
        self.angle = (self.angle + ROTATION_SPEED) % 360  # 顺时针旋转

    def get_vertices(self):
        vertices = []
        for i in range(7):
            theta = math.radians(self.angle + i * 360 / 7)
            x = self.center[0] + self.radius * math.cos(theta)
            y = self.center[1] + self.radius * math.sin(theta)
            vertices.append((x, y))
        return vertices

    # 检查点是否在七边形内（使用射线法）
    def contains_point(self, px, py):
        vertices = self.get_vertices()
        inside = False
        n = len(vertices)
        p1x, p1y = vertices[0]
        for i in range(n + 1):
            p2x, p2y = vertices[i % n]
            if min(p1y, p2y) < py <= max(p1y, p2y) and px <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or px <= xinters:
                    inside = not inside
            p1x, p1y = p2x, p2y
        return inside

class Ball:
    def __init__(self, heptagon):
        self.heptagon = heptagon
        self.reset()
        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.trail = []  # 轨迹 (bonus)

    def reset(self):
        # 随机初始位置（在七边形内）
        while True:
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, RADIUS - BALL_RADIUS)
            self.x = CENTER[0] + r * math.cos(angle)
            self.y = CENTER[1] + r * math.sin(angle)
            if self.heptagon.contains_point(self.x, self.y):
                break
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)

    def update(self):
        # 应用重力
        self.vy += GRAVITY

        # 更新位置
        self.x += self.vx
        self.y += self.vy

        # 更新轨迹 (bonus: 最近100帧)
        self.trail.append((self.x, self.y))
        if len(self.trail) > 100:
            self.trail.pop(0)

    def check_wall_collision(self):
        # 为了处理旋转，使用坐标逆变换：将球移到固定七边形坐标系
        rel_x = self.x - CENTER[0]
        rel_y = self.y - CENTER[1]
        rot_angle = math.radians(-self.heptagon.angle)  # 逆旋转
        rot_x = rel_x * math.cos(rot_angle) - rel_y * math.sin(rot_angle)
        rot_y = rel_x * math.sin(rot_angle) + rel_y * math.cos(rot_angle)

        # 在固定系下检查是否超出（近似使用多边形边碰撞）
        if not self.heptagon.contains_point(self.x, self.y):  # 使用当前旋转的contains
            # 找到最近边并计算法线（简化：使用径向近似为圆，实际应计算边法线）
            # 为准确，计算到中心的向量作为法线（对凸多边形有效近似）
            nx = rel_x / self.heptagon.radius
            ny = rel_y / self.heptagon.radius
            norm = math.sqrt(nx**2 + ny**2)
            if norm > 0:
                nx /= norm
                ny /= norm

            # 变换速度到旋转系（但由于反射在世界系，调整）
            dot = self.vx * nx + self.vy * ny
            self.vx = self.vx - 2 * dot * nx
            self.vy = self.vy - 2 * dot * ny

            # 应用弹性损失
            self.vx *= ELASTICITY
            self.vy *= ELASTICITY

            # 回移位置避免卡住
            self.x -= self.vx
            self.y -= self.vy

def check_ball_collision(ball1, ball2):
    dx = ball1.x - ball2.x
    dy = ball1.y - ball2.y
    dist = math.sqrt(dx**2 + dy**2)
    if dist < 2 * BALL_RADIUS:
        # 动量守恒（假设质量相等）
        nx = dx / dist if dist > 0 else 0
        ny = dy / dist if dist > 0 else 0
        v1 = ball1.vx * nx + ball1.vy * ny
        v2 = ball2.vx * nx + ball2.vy * ny
        ball1.vx -= v1 * nx
        ball1.vy -= v1 * ny
        ball2.vx -= v2 * nx
        ball2.vy -= v2 * ny
        ball1.vx += v2 * nx
        ball1.vy += v2 * ny
        ball2.vx += v1 * nx
        ball2.vy += v1 * ny

        # 弹性损失（平均应用）
        ball1.vx *= ELASTICITY
        ball1.vy *= ELASTICITY
        ball2.vx *= ELASTICITY
        ball2.vy *= ELASTICITY

        # 分开避免重叠
        overlap = 2 * BALL_RADIUS - dist
        ball1.x += nx * overlap / 2
        ball1.y += ny * overlap / 2
        ball2.x -= nx * overlap / 2
        ball2.y -= ny * overlap / 2

# 主程序
heptagon = Heptagon(CENTER, RADIUS)
balls = [Ball(heptagon) for _ in range(NUM_BALLS)]

paused = False
font = pygame.font.SysFont(None, 24)  # 用于FPS (bonus)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_SPACE:
                paused = not paused
            if event.key == pygame.K_r:
                for ball in balls:
                    ball.reset()

    if not paused:
        heptagon.update()

        for ball in balls:
            ball.update()

        # 球-墙碰撞
        for ball in balls:
            ball.check_wall_collision()

        # 球-球碰撞
        for i in range(NUM_BALLS):
            for j in range(i + 1, NUM_BALLS):
                check_ball_collision(balls[i], balls[j])

    # 渲染
    screen.fill(BLACK)

    # 绘制七边形
    pygame.draw.polygon(screen, WHITE, heptagon.get_vertices(), 2)

    # 绘制球和轨迹
    for ball in balls:
        # 轨迹 (bonus: 渐变透明)
        for idx in range(1, len(ball.trail)):
            alpha = int(255 * (idx / len(ball.trail)))
            color = (*ball.color, alpha)
            surf = pygame.Surface((2, 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (1, 1), 1)
            screen.blit(surf, (int(ball.trail[idx-1][0]), int(ball.trail[idx-1][1])))
        pygame.draw.circle(screen, ball.color, (int(ball.x), int(ball.y)), BALL_RADIUS)

    # FPS显示 (bonus)
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
    screen.blit(fps_text, (10, 10))

    pygame.display.flip()
    clock.tick(FPS)