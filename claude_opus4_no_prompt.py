import pygame
import math
import random
import numpy as np
from typing import List, Tuple

# 初始化Pygame
pygame.init()

# 常量定义
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (0, 0, 0)
HEPTAGON_COLOR = (255, 255, 255)
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
NUM_BALLS = 20
GRAVITY = 9.81 * 50  # 像素尺度的重力加速度
ELASTICITY = 0.85
ROTATION_SPEED = 15  # 度/秒
TRAIL_LENGTH = 100  # 轨迹长度

class Ball:
    """球类，处理球的物理属性和行为"""
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-200, 200)  # 像素/秒
        self.vy = random.uniform(-200, 200)
        self.radius = BALL_RADIUS
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.trail = []  # 轨迹点
        self.spin = random.uniform(-360, 360)  # 自旋角速度（度/秒）
        self.angle = 0  # 当前旋转角度
        
    def update(self, dt: float):
        """更新球的位置和速度"""
        # 应用重力
        self.vy += GRAVITY * dt
        
        # 更新位置
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # 更新自旋
        self.angle += self.spin * dt
        
        # 更新轨迹
        self.trail.append((self.x, self.y))
        if len(self.trail) > TRAIL_LENGTH:
            self.trail.pop(0)
            
    def draw(self, screen: pygame.Surface):
        """绘制球和轨迹"""
        # 绘制轨迹
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = i / len(self.trail)
                color = tuple(int(c * alpha) for c in self.color)
                pygame.draw.line(screen, color, self.trail[i-1], self.trail[i], 1)
        
        # 绘制球
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # 绘制自旋指示器
        end_x = self.x + self.radius * 0.8 * math.cos(math.radians(self.angle))
        end_y = self.y + self.radius * 0.8 * math.sin(math.radians(self.angle))
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y), (end_x, end_y), 2)

class Heptagon:
    """正七边形容器类"""
    
    def __init__(self, center_x: float, center_y: float, radius: float):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.angle = 0  # 当前旋转角度
        self.vertices = []
        self.update_vertices()
        
    def update_vertices(self):
        """更新七边形顶点坐标"""
        self.vertices = []
        for i in range(7):
            angle = 2 * math.pi * i / 7 + math.radians(self.angle)
            x = self.center_x + self.radius * math.cos(angle)
            y = self.center_y + self.radius * math.sin(angle)
            self.vertices.append((x, y))
            
    def rotate(self, dt: float):
        """旋转七边形"""
        self.angle += ROTATION_SPEED * dt
        self.update_vertices()
        
    def draw(self, screen: pygame.Surface):
        """绘制七边形"""
        pygame.draw.polygon(screen, HEPTAGON_COLOR, self.vertices, 2)
        
    def get_edges(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """获取所有边"""
        edges = []
        for i in range(7):
            edge = (self.vertices[i], self.vertices[(i + 1) % 7])
            edges.append(edge)
        return edges

def point_to_line_distance(point: Tuple[float, float], line_start: Tuple[float, float], 
                          line_end: Tuple[float, float]) -> Tuple[float, Tuple[float, float]]:
    """计算点到线段的最短距离和最近点"""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    # 线段向量
    dx = x2 - x1
    dy = y2 - y1
    
    # 线段长度的平方
    line_length_sq = dx * dx + dy * dy
    
    if line_length_sq == 0:
        # 线段退化为点
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2), (x1, y1)
    
    # 计算投影参数
    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / line_length_sq))
    
    # 最近点
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # 距离
    distance = math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)
    
    return distance, (closest_x, closest_y)

def check_ball_heptagon_collision(ball: Ball, heptagon: Heptagon) -> bool:
    """检测球与七边形的碰撞"""
    edges = heptagon.get_edges()
    
    for edge in edges:
        distance, closest_point = point_to_line_distance((ball.x, ball.y), edge[0], edge[1])
        
        if distance <= ball.radius:
            # 发生碰撞，计算反弹
            # 计算法向量
            edge_dx = edge[1][0] - edge[0][0]
            edge_dy = edge[1][1] - edge[0][1]
            edge_length = math.sqrt(edge_dx**2 + edge_dy**2)
            
            # 单位法向量（垂直于边）
            normal_x = -edge_dy / edge_length
            normal_y = edge_dx / edge_length
            
            # 确保法向量指向内部
            center_to_ball_x = ball.x - heptagon.center_x
            center_to_ball_y = ball.y - heptagon.center_y
            if normal_x * center_to_ball_x + normal_y * center_to_ball_y > 0:
                normal_x = -normal_x
                normal_y = -normal_y
            
            # 计算速度在法向量上的投影
            velocity_dot_normal = ball.vx * normal_x + ball.vy * normal_y
            
            # 如果球正在远离边界，不处理碰撞
            if velocity_dot_normal >= 0:
                continue
            
            # 反弹速度
            ball.vx -= 2 * velocity_dot_normal * normal_x
            ball.vy -= 2 * velocity_dot_normal * normal_y
            
            # 应用弹性系数
            ball.vx *= ELASTICITY
            ball.vy *= ELASTICITY
            
            # 将球推出边界
            penetration = ball.radius - distance
            ball.x += normal_x * penetration
            ball.y += normal_y * penetration
            
            return True
    
    return False

def check_ball_ball_collision(ball1: Ball, ball2: Ball):
    """检测并处理两球之间的碰撞"""
    dx = ball2.x - ball1.x
    dy = ball2.y - ball1.y
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance < ball1.radius + ball2.radius:
        # 发生碰撞
        # 单位方向向量
        if distance == 0:
            distance = 0.01
        nx = dx / distance
        ny = dy / distance
        
        # 相对速度
        dvx = ball2.vx - ball1.vx
        dvy = ball2.vy - ball1.vy
        
        # 相对速度在碰撞方向上的分量
        dvn = dvx * nx + dvy * ny
        
        # 如果球正在分离，不处理
        if dvn > 0:
            return
        
        # 计算碰撞后的速度（假设质量相等）
        impulse = 2 * dvn / 2  # 对于相等质量
        
        ball1.vx += impulse * nx
        ball1.vy += impulse * ny
        ball2.vx -= impulse * nx
        ball2.vy -= impulse * ny
        
        # 应用弹性系数
        ball1.vx *= ELASTICITY
        ball1.vy *= ELASTICITY
        ball2.vx *= ELASTICITY
        ball2.vy *= ELASTICITY
        
        # 分离重叠的球
        overlap = ball1.radius + ball2.radius - distance
        separate_x = nx * overlap / 2
        separate_y = ny * overlap / 2
        
        ball1.x -= separate_x
        ball1.y -= separate_y
        ball2.x += separate_x
        ball2.y += separate_y

def is_point_inside_heptagon(x: float, y: float, heptagon: Heptagon) -> bool:
    """检查点是否在七边形内部"""
    # 使用射线法
    count = 0
    vertices = heptagon.vertices
    n = len(vertices)
    
    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        
        if ((v1[1] > y) != (v2[1] > y)) and \
           (x < (v2[0] - v1[0]) * (y - v1[1]) / (v2[1] - v1[1]) + v1[0]):
            count += 1
    
    return count % 2 == 1

def main():
    """主函数"""
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("旋转七边形弹跳球模拟器")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    
    # 创建七边形
    heptagon = Heptagon(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, HEPTAGON_RADIUS)
    
    # 创建球
    balls = []
    for _ in range(NUM_BALLS):
        # 在七边形内随机生成球
        while True:
            x = random.uniform(WINDOW_WIDTH // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                             WINDOW_WIDTH // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
            y = random.uniform(WINDOW_HEIGHT // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                             WINDOW_HEIGHT // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
            if is_point_inside_heptagon(x, y, heptagon):
                balls.append(Ball(x, y))
                break
    
    running = True
    paused = False
    show_fps = True
    
    while running:
        dt = clock.tick(FPS) / 1000.0  # 转换为秒
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    # 重置球的位置
                    balls.clear()
                    for _ in range(NUM_BALLS):
                        while True:
                            x = random.uniform(WINDOW_WIDTH // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                                             WINDOW_WIDTH // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
                            y = random.uniform(WINDOW_HEIGHT // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                                             WINDOW_HEIGHT // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
                            if is_point_inside_heptagon(x, y, heptagon):
                                balls.append(Ball(x, y))
                                break
                elif event.key == pygame.K_f:
                    show_fps = not show_fps
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 鼠标点击添加新球
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if is_point_inside_heptagon(mouse_x, mouse_y, heptagon):
                    balls.append(Ball(mouse_x, mouse_y))
        
        if not paused:
            # 更新七边形旋转
            heptagon.rotate(dt)
            
            # 更新球
            for ball in balls:
                ball.update(dt)
            
            # 碰撞检测
            for ball in balls:
                check_ball_heptagon_collision(ball, heptagon)
            
            # 球与球之间的碰撞
            for i in range(len(balls)):
                for j in range(i + 1, len(balls)):
                    check_ball_ball_collision(balls[i], balls[j])
        
        # 绘制
        screen.fill(BACKGROUND_COLOR)
        
        # 绘制七边形
        heptagon.draw(screen)
        
        # 绘制球
        for ball in balls:
            ball.draw(screen)
        
        # 显示信息
        if show_fps:
            fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (255, 255, 255))
            screen.blit(fps_text, (10, 10))
        
        ball_count_text = font.render(f"Balls: {len(balls)}", True, (255, 255, 255))
        screen.blit(ball_count_text, (10, 50))
        
        if paused:
            pause_text = font.render("PAUSED", True, (255, 0, 0))
            screen.blit(pause_text, (WINDOW_WIDTH // 2 - 50, 10))
        
        # 显示控制说明
        controls = [
            "Controls:",
            "Space: Pause/Resume",
            "R: Reset balls",
            "F: Toggle FPS",
            "Mouse: Add ball",
            "ESC: Exit"
        ]
        y_offset = WINDOW_HEIGHT - 180
        small_font = pygame.font.Font(None, 24)
        for control in controls:
            control_text = small_font.render(control, True, (200, 200, 200))
            screen.blit(control_text, (10, y_offset))
            y_offset += 25
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()