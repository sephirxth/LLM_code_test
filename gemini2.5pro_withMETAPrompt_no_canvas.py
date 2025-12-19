# -*- coding: utf-8 -*-
import pygame
import numpy as np
import random
from collections import deque

# --- 核心参数与常量 ---

# 技术规格
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60
HEPTAGON_RADIUS = 300
HEPTAGON_CENTER = np.array([WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2])
BALL_RADIUS = 8
NUM_BALLS = 20

# 物理模拟参数
GRAVITY = np.array([0, 250])  # 重力加速度 (pixels/s^2)，调大一点视觉效果更明显
ELASTICITY = 0.85  # 弹性系数
ROTATION_SPEED_DEG = 15  # 七边形旋转速度 (degrees/s)

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# --- 辅助函数 ---

def get_random_color():
    """生成一个鲜艳的随机颜色"""
    return (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

# --- 主要类定义 ---

class Heptagon:
    """
    管理旋转七边形容器的类
    """
    def __init__(self, center, radius, rotation_speed_deg):
        self.center = center
        self.radius = radius
        self.num_sides = 7
        self.rotation_speed = np.deg2rad(rotation_speed_deg)  # 转换为弧度/秒
        self.angle = 0.0  # 当前旋转角度 (弧度)
        self.vertices = self.get_vertices()

    def get_vertices(self):
        """根据当前旋转角度计算世界坐标系下的顶点"""
        points = []
        for i in range(self.num_sides):
            theta = 2 * np.pi * i / self.num_sides + self.angle
            x = self.center[0] + self.radius * np.cos(theta)
            y = self.center[1] + self.radius * np.sin(theta)
            points.append(np.array([x, y]))
        return points

    def update(self, dt):
        """更新七边形的旋转角度"""
        self.angle += self.rotation_speed * dt
        self.vertices = self.get_vertices()

    def draw(self, screen):
        """绘制七边形边界"""
        pygame.draw.polygon(screen, WHITE, self.vertices, 2)


class Ball:
    """
    管理单个弹跳球的类
    """
    def __init__(self, container_center, container_radius):
        self.radius = BALL_RADIUS
        self.color = get_random_color()
        # 在容器内生成随机位置
        while True:
            r = random.uniform(0, container_radius - self.radius)
            theta = random.uniform(0, 2 * np.pi)
            self.pos = container_center + np.array([r * np.cos(theta), r * np.sin(theta)])
            if np.linalg.norm(self.pos - container_center) < container_radius - self.radius:
                 break
        
        self.vel = np.array([random.uniform(-100, 100), random.uniform(-100, 100)], dtype=float) # 随机初始速度 (pixels/s)
        self.mass = 1.0 # 假设所有球质量相同

        # 附加挑战：轨迹和自旋
        self.history = deque(maxlen=100)
        self.spin_angle = 0
        self.spin_speed = random.uniform(-180, 180) # 随机自旋速度

    def update(self, dt, gravity):
        """更新球的位置和速度"""
        self.vel += gravity * dt
        self.pos += self.vel * dt
        
        # 更新轨迹和自旋
        self.history.append(tuple(self.pos.astype(int)))
        self.spin_angle += self.spin_speed * dt


    def draw(self, screen):
        """绘制球体"""
        # 绘制球
        pygame.draw.circle(screen, self.color, self.pos.astype(int), self.radius)
        # 绘制自旋指示线
        end_pos_x = self.pos[0] + self.radius * np.cos(np.deg2rad(self.spin_angle))
        end_pos_y = self.pos[1] + self.radius * np.sin(np.deg2rad(self.spin_angle))
        pygame.draw.line(screen, BLACK, self.pos.astype(int), (int(end_pos_x), int(end_pos_y)), 1)


    def draw_trail(self, screen):
        """绘制球的轨迹"""
        if len(self.history) > 2:
            try:
                 pygame.draw.aalines(screen, self.color, False, list(self.history), 1)
            except TypeError: # 忽略可能因类型转换失败的罕见错误
                 pass


# --- 核心物理与碰撞处理函数 ---

def handle_wall_collisions(ball, heptagon, elasticity):
    """处理球与旋转七边形边界的碰撞"""
    vertices = heptagon.vertices
    num_vertices = len(vertices)

    for i in range(num_vertices):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % num_vertices]
        
        edge = p2 - p1
        edge_norm = np.array([-edge[1], edge[0]]) # 边的法向量，指向多边形内部
        edge_norm = edge_norm / np.linalg.norm(edge_norm)

        # 向量从边上的点p1到球心
        vec_to_ball = ball.pos - p1
        
        # 球心到边的垂直距离
        dist_to_edge = vec_to_ball.dot(edge_norm)

        if dist_to_edge < ball.radius:
            # 1. 修正位置，防止球穿透边界
            overlap = ball.radius - dist_to_edge
            ball.pos += overlap * edge_norm

            # 2. 计算碰撞后的速度
            # 相对速度的法向分量
            vel_normal_comp = ball.vel.dot(edge_norm)
            
            # 只有当球正在朝墙壁移动时才反弹
            if vel_normal_comp < 0:
                # 反射速度向量
                # v_new = v - (1 + e) * (v . n) * n
                ball.vel -= (1 + elasticity) * vel_normal_comp * edge_norm

def handle_ball_collisions(ball1, ball2, elasticity):
    """处理球与球之间的碰撞"""
    delta_pos = ball1.pos - ball2.pos
    dist = np.linalg.norm(delta_pos)
    
    # 检查是否碰撞
    if dist < ball1.radius + ball2.radius:
        # 1. 修正位置，防止重叠
        overlap = (ball1.radius + ball2.radius) - dist
        # 沿碰撞法线方向将球分开
        correction_vec = delta_pos / dist
        ball1.pos += correction_vec * overlap / 2
        ball2.pos -= correction_vec * overlap / 2
        
        # 2. 计算碰撞后的速度 (基于动量守恒和能量守恒)
        # 碰撞法线
        normal = delta_pos / dist
        # 碰撞切线
        tangent = np.array([-normal[1], normal[0]])

        # 速度在法线和切线方向上的投影
        v1n = ball1.vel.dot(normal)
        v1t = ball1.vel.dot(tangent)
        v2n = ball2.vel.dot(normal)
        v2t = ball2.vel.dot(tangent)

        # 切向速度不变
        # 法向速度根据一维弹性碰撞公式交换（此处考虑弹性系数）
        # m1*v1n + m2*v2n = m1*v1n_new + m2*v2n_new
        # v1n_new - v2n_new = -e * (v1n - v2n)
        # 假设质量相等 (m1=m2=1)
        v1n_new = (v1n * (ball1.mass - elasticity * ball2.mass) + (1 + elasticity) * ball2.mass * v2n) / (ball1.mass + ball2.mass)
        v2n_new = (v2n * (ball2.mass - elasticity * ball1.mass) + (1 + elasticity) * ball1.mass * v1n) / (ball1.mass + ball2.mass)

        # 将新的法向速度与旧的切向速度组合成新的速度向量
        ball1.vel = v1n_new * normal + v1t * tangent
        ball2.vel = v2n_new * normal + v2t * tangent

# --- 主程序 ---

def main():
    """主游戏循环"""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Bouncing Balls in a Rotating Heptagon")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24)

    # 创建对象
    heptagon = Heptagon(HEPTAGON_CENTER, HEPTAGON_RADIUS, ROTATION_SPEED_DEG)
    balls = [Ball(HEPTAGON_CENTER, HEPTAGON_RADIUS) for _ in range(NUM_BALLS)]

    # 游戏状态
    running = True
    paused = False
    show_trails = False # 轨迹默认关闭，按'T'开启

    while running:
        # --- 1. 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    # 重置所有球
                    balls = [Ball(HEPTAGON_CENTER, HEPTAGON_RADIUS) for _ in range(NUM_BALLS)]
                if event.key == pygame.K_t: # 附加功能：切换轨迹显示
                    show_trails = not show_trails
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # 附加功能：鼠标左键添加新球
                new_ball = Ball(HEPTAGON_CENTER, HEPTAGON_RADIUS)
                new_ball.pos = np.array(event.pos, dtype=float)
                balls.append(new_ball)


        # --- 2. 逻辑更新 (如果未暂停) ---
        if not paused:
            dt = clock.get_time() / 1000.0  # 转换为秒

            # 更新七边形
            heptagon.update(dt)

            # 更新所有球
            for ball in balls:
                ball.update(dt, GRAVITY)

            # 处理碰撞
            # 迭代多次以提高稳定性，防止物体快速穿透
            for _ in range(3): # Sub-stepping for stability
                # 球与墙壁
                for ball in balls:
                    handle_wall_collisions(ball, heptagon, ELASTICITY)
                
                # 球与球
                for i in range(len(balls)):
                    for j in range(i + 1, len(balls)):
                        handle_ball_collisions(balls[i], balls[j], ELASTICITY)

        # --- 3. 渲染 ---
        screen.fill(BLACK)

        # 绘制七边形
        heptagon.draw(screen)
        
        # 绘制轨迹（如果开启）
        if show_trails:
            for ball in balls:
                ball.draw_trail(screen)
        
        # 绘制球
        for ball in balls:
            ball.draw(screen)

        # 绘制状态信息和FPS (附加功能)
        fps_text = font.render(f"FPS: {clock.get_fps():.1f}", True, WHITE)
        screen.blit(fps_text, (10, 10))

        ball_count_text = font.render(f"Balls: {len(balls)}", True, WHITE)
        screen.blit(ball_count_text, (10, 40))

        if paused:
            pause_text = font.render("PAUSED", True, RED)
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
            screen.blit(pause_text, text_rect)

        # --- 4. 更新显示 ---
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == '__main__':
    main()