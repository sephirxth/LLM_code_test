# -*- coding: utf-8 -*-
"""
旋转七边形容器中的弹跳球物理模拟

核心功能:
- 创建一个顺时针旋转的正七边形容器。
- 在容器内模拟20个小球的物理运动。
- 实现小球之间、小球与旋转边界之间的精确碰撞检测与响应。
- 模拟重力、弹性碰撞等物理效应。

交互控制:
- [空格键]: 暂停/恢复模拟。
- [R键]: 重置所有小球的状态。
- [ESC键]: 退出程序。
- [鼠标左键点击]: 在点击位置添加一个新的小球。

附加挑战功能:
- 小球轨迹跟踪: 显示每个小球最近100帧的运动路径。
- FPS监控: 在屏幕左上角实时显示当前帧率。
"""
import pygame
import random
import math
from collections import deque

# --- 1. 初始化与常量定义 (Initialization and Constants) ---

# Pygame 初始化
pygame.init()

# 屏幕尺寸
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
# 七边形半径
HEPTAGON_RADIUS = 300
# 小球数量与半径
BALL_COUNT = 20
BALL_RADIUS = 8
# 物理参数
GRAVITY = pygame.Vector2(0, 9.81 * 10) # 乘以10以在像素空间获得更好的视觉效果
ELASTICITY = 0.85 # 弹性系数
# 动画参数
FPS = 60
ROTATION_SPEED_DEG = 15  # 每秒旋转15度
ROTATION_SPEED_RAD = math.radians(ROTATION_SPEED_DEG) # 转换为弧度

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREY = (50, 50, 50)

# --- 2. 辅助类与函数 (Helper Classes and Functions) ---

def get_random_color():
    """生成一个鲜艳的随机颜色"""
    return (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

# --- 3. 核心类定义 (Core Classes) ---

class Ball:
    """
    定义小球对象的类
    - 存储位置、速度、颜色等属性
    - 处理物理更新（重力、运动）
    - 绘制小球及其轨迹
    """
    def __init__(self, position, velocity, radius, color):
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(velocity)
        self.radius = radius
        self.color = color
        self.mass = radius ** 2 # 质量与半径的平方成正比
        # 用于轨迹跟踪的双端队列
        self.trail = deque(maxlen=100)

    def update(self, dt):
        """
        更新小球状态
        - 应用重力
        - 更新速度和位置
        - 记录轨迹点
        """
        # 应用重力
        self.vel += GRAVITY * dt
        # 更新位置
        self.pos += self.vel * dt
        # 添加当前位置到轨迹
        self.trail.append(tuple(self.pos))

    def draw(self, surface):
        """在给定的surface上绘制小球及其轨迹"""
        # 绘制小球
        pygame.draw.circle(surface, self.color, self.pos, self.radius)
        
        # 绘制轨迹
        if len(self.trail) > 2:
            # 创建轨迹点的副本以避免在迭代时修改
            trail_points = list(self.trail)
            for i in range(len(trail_points) - 1):
                start_pos = trail_points[i]
                end_pos = trail_points[i+1]
                # 计算透明度，让轨迹渐隐
                alpha = int(255 * (i / len(self.trail)))
                trail_color = self.color + (alpha,)
                
                # 创建一个带alpha通道的临时surface来绘制半透明线条
                line_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(line_surf, trail_color, start_pos, end_pos, 1)
                surface.blit(line_surf, (0, 0))


class Heptagon:
    """
    定义旋转七边形容器的类
    - 计算顶点
    - 处理旋转
    - 绘制边框
    """
    def __init__(self, center, radius):
        self.center = pygame.Vector2(center)
        self.radius = radius
        self.angle = 0  # 当前旋转角度（弧度）
        self.num_sides = 7
        self.vertices = []
        self.update_vertices()

    def update_vertices(self):
        """根据当前旋转角度计算七边形的顶点坐标"""
        self.vertices = []
        angle_step = 2 * math.pi / self.num_sides
        for i in range(self.num_sides):
            angle = i * angle_step + self.angle
            x = self.center.x + self.radius * math.cos(angle)
            y = self.center.y + self.radius * math.sin(angle)
            self.vertices.append(pygame.Vector2(x, y))

    def update(self, dt):
        """更新旋转角度并重新计算顶点"""
        self.angle += ROTATION_SPEED_RAD * dt
        self.update_vertices()

    def draw(self, surface):
        """在给定的surface上绘制七边形边框"""
        pygame.draw.polygon(surface, WHITE, self.vertices, 2)


# --- 4. 物理与碰撞处理 (Physics and Collision Handling) ---

def handle_ball_collisions(balls):
    """处理所有小球之间的碰撞"""
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            ball1 = balls[i]
            ball2 = balls[j]

            dist_vec = ball1.pos - ball2.pos
            dist = dist_vec.length()
            min_dist = ball1.radius + ball2.radius

            if dist < min_dist:
                # 碰撞发生
                
                # 1. 防止重叠：将小球沿碰撞法线方向移开
                overlap = min_dist - dist
                push_vec = dist_vec.normalize() * overlap
                ball1.pos += push_vec * 0.5
                ball2.pos -= push_vec * 0.5

                # 2. 计算碰撞响应（动量守恒）
                # 碰撞法线
                normal = dist_vec.normalize()
                # 相对速度
                relative_vel = ball1.vel - ball2.vel
                # 沿法线方向的相对速度分量
                vel_along_normal = relative_vel.dot(normal)

                # 如果小球正在远离，则不处理
                if vel_along_normal > 0:
                    continue

                # 计算冲量
                e = ELASTICITY
                m1, m2 = ball1.mass, ball2.mass
                impulse_scalar = -(1 + e) * vel_along_normal / (1 / m1 + 1 / m2)
                
                impulse_vec = impulse_scalar * normal

                # 应用冲量更新速度
                ball1.vel += impulse_vec / m1
                ball2.vel -= impulse_vec / m2

def handle_wall_collisions(ball, heptagon):
    """处理单个小球与旋转七边形边界的碰撞"""
    for i in range(heptagon.num_sides):
        p1 = heptagon.vertices[i]
        p2 = heptagon.vertices[(i + 1) % heptagon.num_sides]

        # 边向量
        edge = p2 - p1
        # 边的法线（指向七边形内部）
        normal = pygame.Vector2(-edge.y, edge.x).normalize()

        # 小球中心到边起点的向量
        ball_to_p1 = ball.pos - p1
        
        # 计算小球中心到边的距离
        dist_to_edge = ball_to_p1.dot(normal)

        if dist_to_edge < ball.radius:
            # 碰撞发生
            
            # 1. 防止穿透：将小球沿法线方向移回边界内
            penetration = ball.radius - dist_to_edge
            ball.pos += normal * penetration

            # 2. 计算碰撞响应
            # 沿法线方向的速度分量
            vel_normal_comp = ball.vel.dot(normal)
            
            # 反射速度分量并应用弹性系数
            new_vel_normal_comp = -vel_normal_comp * ELASTICITY
            
            # 计算速度变化量并应用
            vel_change = (new_vel_normal_comp - vel_normal_comp) * normal
            ball.vel += vel_change

# --- 5. 主游戏循环 (Main Game Loop) ---

def main():
    """主函数，包含游戏循环"""
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("旋转七边形中的弹跳球")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    # 创建对象实例
    heptagon = Heptagon((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), HEPTAGON_RADIUS)
    
    balls = []
    def reset_balls():
        """重置或初始化所有小球"""
        nonlocal balls
        balls.clear()
        for _ in range(BALL_COUNT):
            # 在七边形内生成随机位置
            while True:
                r = random.uniform(0, heptagon.radius - BALL_RADIUS * 2)
                theta = random.uniform(0, 2 * math.pi)
                pos = heptagon.center + pygame.Vector2(r * math.cos(theta), r * math.sin(theta))
                
                # 检查确保新球不会与其他球重叠
                is_overlapping = False
                for other_ball in balls:
                    if pos.distance_to(other_ball.pos) < BALL_RADIUS * 2:
                        is_overlapping = True
                        break
                if not is_overlapping:
                    break
            
            vel = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
            color = get_random_color()
            balls.append(Ball(pos, vel, BALL_RADIUS, color))

    reset_balls()

    running = True
    paused = False

    while running:
        # 时间增量 (delta time)，确保物理计算与帧率无关
        dt = clock.tick(FPS) / 1000.0

        # --- 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    reset_balls()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 鼠标左键
                if not paused:
                    pos = pygame.mouse.get_pos()
                    # 检查点击位置是否在七边形内
                    dist_from_center = pygame.Vector2(pos).distance_to(heptagon.center)
                    if dist_from_center < heptagon.radius - BALL_RADIUS:
                        vel = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
                        color = get_random_color()
                        balls.append(Ball(pos, vel, BALL_RADIUS, color))


        # --- 更新逻辑 ---
        if not paused:
            # 更新七边形
            heptagon.update(dt)
            # 更新所有小球
            for ball in balls:
                ball.update(dt)
            
            # 处理碰撞
            handle_ball_collisions(balls)
            for ball in balls:
                handle_wall_collisions(ball, heptagon)

        # --- 渲染/绘制 ---
        screen.fill(BLACK)

        # 绘制七边形
        heptagon.draw(screen)

        # 绘制所有小球
        for ball in balls:
            ball.draw(screen)

        # 绘制FPS
        current_fps = clock.get_fps()
        fps_text = font.render(f"FPS: {current_fps:.2f}", True, WHITE)
        screen.blit(fps_text, (10, 10))
        
        # 绘制暂停提示
        if paused:
            pause_text = font.render("PAUSED", True, RED)
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            screen.blit(pause_text, text_rect)

        # 更新显示
        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
