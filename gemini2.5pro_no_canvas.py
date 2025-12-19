# -*- coding: utf-8 -*-

import pygame
import random
import math
from collections import deque

# --- 核心常量 ---

# 技术规格
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
BALL_COUNT = 20

# 物理模拟参数
GRAVITY = 9.81 * 100  # 重力加速度 (g = 9.81 m/s^2, 1米=100像素)
ELASTICITY = 0.85     # 弹性系数 (碰撞后保留85%的垂直速度)
ROTATION_SPEED = 15   # 七边形旋转速度 (度/秒)

# 颜色定义
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREY = (50, 50, 50)

# --- 辅助函数 ---

def get_random_color():
    """返回一个随机的、鲜艳的颜色"""
    return (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

def is_point_in_polygon(point, polygon_vertices):
    """
    使用射线法检测一个点是否在多边形内部。
    从点向右发出射线，计算与多边形边的交点数量。
    奇数则在内部，偶数则在外部。
    """
    x, y = point
    n = len(polygon_vertices)
    inside = False
    p1x, p1y = polygon_vertices[0]
    for i in range(n + 1):
        p2x, p2y = polygon_vertices[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


# --- 主要类定义 ---

class Ball:
    """
    球体类，管理球的位置、速度、颜色和物理行为
    """
    def __init__(self, container_vertices):
        self.radius = BALL_RADIUS
        self.color = get_random_color()
        self.position = self._get_random_position(container_vertices)
        # 初始速度随机
        self.velocity = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
        # 附加挑战: 轨迹跟踪
        self.trail = deque(maxlen=100)

    def _get_random_position(self, container_vertices):
        """在容器内生成一个随机的有效初始位置"""
        while True:
            pos = pygame.Vector2(
                random.uniform(-HEPTAGON_RADIUS, HEPTAGON_RADIUS),
                random.uniform(-HEPTAGON_RADIUS, HEPTAGON_RADIUS)
            )
            # 在一个简化的正方形内快速筛选，然后用精确的多边形算法验证
            if pos.length() < HEPTAGON_RADIUS:
                # 假设中心为(0,0)进行初始位置判断
                local_center = pygame.Vector2(0, 0)
                local_vertices = [v - (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2) for v in container_vertices]
                if is_point_in_polygon(pos, local_vertices):
                    return pos + pygame.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)


    def update(self, dt, paused):
        """
        更新球的状态 (位置和速度)
        dt: delta time, 时间增量，用于实现帧率无关的物理计算
        """
        if not paused:
            # 1. 应用重力
            self.velocity.y += GRAVITY * dt
            # 2. 更新位置
            self.position += self.velocity * dt
            # 3. 更新轨迹
            self.trail.append(self.position.copy())

    def draw(self, screen):
        """在屏幕上绘制球体和其轨迹"""
        # 绘制轨迹
        if len(self.trail) > 2:
            try:
                # 使用 pygame.draw.lines 绘制平滑轨迹
                # trail_alpha = [ (p[0],p[1]) for p in self.trail]
                pygame.draw.lines(screen, self.color, False, list(self.trail), 1)
            except TypeError: # 如果轨迹点太少会报错
                pass
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, self.position, self.radius)

    def resolve_overlap(self, other_ball):
        """解决两个球重叠的问题，将它们沿碰撞法线分开"""
        dist_vec = self.position - other_ball.position
        dist = dist_vec.length()
        overlap = self.radius + other_ball.radius - dist
        if overlap > 0:
            # 沿法线方向移动两个球，使它们刚好接触
            move_vec = dist_vec.normalize() * (overlap / 2)
            self.position += move_vec
            other_ball.position -= move_vec

class Heptagon:
    """
    七边形容器类，管理其旋转和顶点
    """
    def __init__(self, center, radius):
        self.center = pygame.Vector2(center)
        self.radius = radius
        self.angle = 0  # 当前旋转角度 (度)
        self.num_vertices = 7
        self.static_vertices = self._calculate_vertices(0) # 未旋转时的顶点 (局部坐标)
        self.rotated_vertices = self.static_vertices # 当前旋转后的顶点 (世界坐标)

    def _calculate_vertices(self, angle_offset):
        """计算给定旋转角度下的七边形顶点坐标"""
        vertices = []
        angle_step = 360 / self.num_vertices
        for i in range(self.num_vertices):
            angle = math.radians(i * angle_step + angle_offset)
            x = self.center.x + self.radius * math.cos(angle)
            y = self.center.y + self.radius * math.sin(angle)
            vertices.append(pygame.Vector2(x, y))
        return vertices

    def update(self, dt, paused):
        """更新七边形的旋转角度和顶点位置"""
        if not paused:
            self.angle += ROTATION_SPEED * dt
            self.angle %= 360
        self.rotated_vertices = self._calculate_vertices(self.angle)

    def draw(self, screen):
        """在屏幕上绘制七边形"""
        pygame.draw.polygon(screen, COLOR_WHITE, self.rotated_vertices, 2)


# --- 物理引擎函数 ---

def handle_collisions(balls, heptagon, elasticity):
    """主碰撞处理函数，包括球与球以及球与边界"""
    
    # 1. 球与球之间的碰撞
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            ball1 = balls[i]
            ball2 = balls[j]
            
            dist_vec = ball1.position - ball2.position
            dist = dist_vec.length()

            if dist < ball1.radius + ball2.radius:
                # 发生碰撞
                ball1.resolve_overlap(ball2) # 解决重叠问题
                
                # 动量守恒计算
                normal = dist_vec.normalize()
                tangent = pygame.Vector2(-normal.y, normal.x)

                # 将速度投影到法线和切线方向
                v1n = ball1.velocity.dot(normal)
                v1t = ball1.velocity.dot(tangent)
                v2n = ball2.velocity.dot(normal)
                v2t = ball2.velocity.dot(tangent)

                # 碰撞后法线方向的速度 (弹性碰撞公式，质量相等)
                v1n_new = v2n
                v2n_new = v1n
                
                # 将新的法线速度和旧的切线速度组合成新的速度向量
                ball1.velocity = normal * v1n_new + tangent * v1t
                ball2.velocity = normal * v2n_new + tangent * v2t


    # 2. 球与旋转七边形边界的碰撞
    center = heptagon.center
    angle_rad = math.radians(heptagon.angle)
    
    for ball in balls:
        # --- 坐标系变换：将球的坐标变换到七边形的局部坐标系 ---
        # a. 平移到原点
        pos_relative = ball.position - center
        # b. 旋转 (使用相反的角度)
        local_pos = pos_relative.rotate(-heptagon.angle)
        local_vel = ball.velocity.rotate(-heptagon.angle)

        # --- 在局部坐标系中进行碰撞检测和响应 ---
        for i in range(heptagon.num_vertices):
            p1 = heptagon.static_vertices[i] - center
            p2 = heptagon.static_vertices[(i + 1) % heptagon.num_vertices] - center
            
            edge = p2 - p1
            normal = edge.rotate(90).normalize() # 法线指向多边形内部

            # 向量：从边的一个顶点到球心
            vec_to_ball = local_pos - p1
            
            # 球心到边的垂直距离
            dist_to_edge = vec_to_ball.dot(normal)

            if dist_to_edge < ball.radius:
                # 发生碰撞
                
                # a. 修正位置，防止球穿透边界
                penetration = ball.radius - dist_to_edge
                local_pos += normal * penetration
                
                # b. 物理响应：反射速度并应用弹性系数
                v_perp = local_vel.dot(normal) * normal # 垂直分量
                v_para = local_vel - v_perp           # 平行分量
                
                # 新的速度 = 平行分量 - 弹性系数 * 垂直分量
                local_vel = v_para - v_perp * elasticity
                
                # --- 将计算出的新坐标和速度变换回世界坐标系 ---
                # a. 旋转回来
                ball.position = local_pos.rotate(heptagon.angle) + center
                ball.velocity = local_vel.rotate(heptagon.angle)
                
                break # 每次只处理一次碰撞，防止重复计算


# --- 主程序 ---

def main():
    """程序主入口"""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("旋转七边形内的弹跳球")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)

    # 创建七边形和球
    heptagon = Heptagon((WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2), HEPTAGON_RADIUS)
    
    def reset_simulation():
        """重置模拟，生成新的球"""
        # 传递初始的七边形顶点，以确保球生成在内部
        initial_verts = heptagon._calculate_vertices(0)
        return [Ball(initial_verts) for _ in range(BALL_COUNT)]

    balls = reset_simulation()

    running = True
    paused = False

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
                    balls = reset_simulation()
            # 附加挑战: 鼠标点击添加新球
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_point_in_polygon(event.pos, heptagon.rotated_vertices):
                    new_ball = Ball(heptagon.rotated_vertices)
                    new_ball.position = pygame.Vector2(event.pos)
                    balls.append(new_ball)

        # --- 2. 游戏状态更新 ---
        dt = clock.tick(FPS) / 1000.0  # 获取自上一帧以来的时间（秒）
        
        heptagon.update(dt, paused)
        for ball in balls:
            ball.update(dt, paused)
        
        if not paused:
            # 执行多次碰撞检测可以提高稳定性
            for _ in range(2): # Sub-steps for stability
                 handle_collisions(balls, heptagon, ELASTICITY)


        # --- 3. 渲染 ---
        screen.fill(COLOR_BLACK)

        # 绘制所有球体
        for ball in balls:
            ball.draw(screen)

        # 绘制七边形容器
        heptagon.draw(screen)

        # --- 4. 显示信息 (UI) ---
        # 附加挑战: 显示FPS
        fps_text = font.render(f"FPS: {clock.get_fps():.1f}", True, COLOR_WHITE)
        screen.blit(fps_text, (10, 10))

        # 显示球的数量
        ball_count_text = font.render(f"Balls: {len(balls)}", True, COLOR_WHITE)
        screen.blit(ball_count_text, (10, 35))

        # 显示暂停状态
        if paused:
            pause_text = font.render("PAUSED", True, COLOR_WHITE)
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH / 2, 50))
            screen.blit(pause_text, text_rect)
        
        # 显示帮助信息
        help_text = font.render("SPACE: Pause/Resume | R: Reset | ESC: Quit | Click to Add", True, COLOR_GREY)
        help_rect = help_text.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30))
        screen.blit(help_text, help_rect)

        # 更新显示
        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()