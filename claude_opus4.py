import pygame
import math
import random
import numpy as np
from collections import deque

# 初始化Pygame
pygame.init()

# 常量定义
WINDOW_SIZE = 800
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
NUM_BALLS = 20
GRAVITY = 9.81 / 60  # 转换为每帧的重力加速度
ELASTICITY = 0.85
ROTATION_SPEED = 15  # 度/秒
FPS = 60
BACKGROUND_COLOR = (0, 0, 0)
HEPTAGON_COLOR = (255, 255, 255)
TRAIL_LENGTH = 100  # 轨迹长度

class Ball:
    """球体类，包含位置、速度、颜色等属性"""
    def __init__(self, x, y):
        self.pos = np.array([x, y], dtype=float)
        self.vel = np.array([random.uniform(-5, 5), random.uniform(-5, 5)], dtype=float)
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.trail = deque(maxlen=TRAIL_LENGTH)  # 轨迹历史
        self.spin = random.uniform(-5, 5)  # 自旋速度
        self.angle = 0  # 当前旋转角度
        
    def update(self):
        """更新球的位置和速度"""
        self.vel[1] += GRAVITY  # 应用重力
        self.pos += self.vel
        self.angle += self.spin  # 更新自旋角度
        self.trail.append(self.pos.copy())  # 记录轨迹
        
    def draw(self, screen):
        """绘制球体和轨迹"""
        # 绘制轨迹
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = int(255 * i / len(self.trail))
                color = (*self.color, alpha)
                pygame.draw.line(screen, color[:3], 
                               self.trail[i-1].astype(int), 
                               self.trail[i].astype(int), 1)
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, self.pos.astype(int), BALL_RADIUS)
        
        # 绘制自旋指示器
        end_x = self.pos[0] + BALL_RADIUS * 0.7 * math.cos(self.angle)
        end_y = self.pos[1] + BALL_RADIUS * 0.7 * math.sin(self.angle)
        pygame.draw.line(screen, (255, 255, 255), self.pos.astype(int), 
                        (int(end_x), int(end_y)), 2)

class RotatingHeptagon:
    """旋转七边形容器类"""
    def __init__(self, center, radius):
        self.center = np.array(center, dtype=float)
        self.radius = radius
        self.angle = 0  # 当前旋转角度
        self.vertices = []
        self.update_vertices()
        
    def update_vertices(self):
        """更新七边形顶点位置"""
        self.vertices = []
        for i in range(7):
            # 计算每个顶点的角度（考虑旋转）
            vertex_angle = self.angle + (2 * math.pi * i / 7)
            x = self.center[0] + self.radius * math.cos(vertex_angle)
            y = self.center[1] + self.radius * math.sin(vertex_angle)
            self.vertices.append(np.array([x, y]))
            
    def rotate(self, dt):
        """旋转七边形"""
        self.angle += math.radians(ROTATION_SPEED) * dt
        self.update_vertices()
        
    def draw(self, screen):
        """绘制七边形"""
        pygame.draw.polygon(screen, HEPTAGON_COLOR, 
                          [v.astype(int) for v in self.vertices], 2)
        
    def get_edges(self):
        """获取七边形的所有边"""
        edges = []
        for i in range(7):
            edge = (self.vertices[i], self.vertices[(i + 1) % 7])
            edges.append(edge)
        return edges

def point_to_line_distance(point, line_start, line_end):
    """计算点到线段的最短距离"""
    line_vec = line_end - line_start
    point_vec = point - line_start
    line_len = np.linalg.norm(line_vec)
    
    if line_len == 0:
        return np.linalg.norm(point_vec)
    
    line_unitvec = line_vec / line_len
    proj_length = np.dot(point_vec, line_unitvec)
    
    if proj_length < 0:
        return np.linalg.norm(point_vec)
    elif proj_length > line_len:
        return np.linalg.norm(point - line_end)
    else:
        proj_point = line_start + line_unitvec * proj_length
        return np.linalg.norm(point - proj_point)

def ball_edge_collision(ball, edge):
    """检测并处理球与边的碰撞"""
    line_start, line_end = edge
    
    # 计算球心到边的距离
    dist = point_to_line_distance(ball.pos, line_start, line_end)
    
    if dist < BALL_RADIUS:
        # 计算边的法向量
        edge_vec = line_end - line_start
        edge_normal = np.array([-edge_vec[1], edge_vec[0]])
        edge_normal = edge_normal / np.linalg.norm(edge_normal)
        
        # 确保法向量指向七边形内部
        center = (line_start + line_end) / 2
        if np.dot(edge_normal, ball.pos - center) < 0:
            edge_normal = -edge_normal
        
        # 将球推出边界
        penetration = BALL_RADIUS - dist
        ball.pos += edge_normal * penetration
        
        # 反射速度
        vel_normal = np.dot(ball.vel, edge_normal)
        if vel_normal < 0:
            ball.vel -= 2 * vel_normal * edge_normal
            ball.vel *= ELASTICITY
            
            # 添加旋转效应
            tangent = np.array([edge_vec[1], -edge_vec[0]])
            tangent = tangent / np.linalg.norm(tangent)
            tangent_vel = np.dot(ball.vel, tangent)
            ball.spin = -tangent_vel * 0.1

def ball_ball_collision(ball1, ball2):
    """检测并处理球与球的碰撞"""
    dist_vec = ball2.pos - ball1.pos
    dist = np.linalg.norm(dist_vec)
    
    if dist < 2 * BALL_RADIUS:
        # 分离重叠的球
        overlap = 2 * BALL_RADIUS - dist
        if dist > 0:
            direction = dist_vec / dist
            ball1.pos -= direction * overlap / 2
            ball2.pos += direction * overlap / 2
        
        # 计算碰撞响应
        if dist > 0:
            normal = dist_vec / dist
            
            # 相对速度
            relative_vel = ball2.vel - ball1.vel
            vel_along_normal = np.dot(relative_vel, normal)
            
            # 如果球正在分离，不处理
            if vel_along_normal > 0:
                return
            
            # 计算碰撞后的速度
            impulse = 2 * vel_along_normal / 2  # 假设相同质量
            ball1.vel += impulse * normal * ELASTICITY
            ball2.vel -= impulse * normal * ELASTICITY

def is_inside_heptagon(point, heptagon):
    """检查点是否在七边形内部"""
    # 使用射线投射算法
    count = 0
    vertices = heptagon.vertices
    n = len(vertices)
    
    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        
        if ((v1[1] > point[1]) != (v2[1] > point[1])) and \
           (point[0] < (v2[0] - v1[0]) * (point[1] - v1[1]) / (v2[1] - v1[1]) + v1[0]):
            count += 1
    
    return count % 2 == 1

def main():
    """主函数"""
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("旋转七边形物理模拟器")
    clock = pygame.time.Clock()
    
    # 创建七边形
    heptagon = RotatingHeptagon((WINDOW_SIZE // 2, WINDOW_SIZE // 2), HEPTAGON_RADIUS)
    
    # 创建球体
    balls = []
    for _ in range(NUM_BALLS):
        # 在七边形内部随机生成球
        while True:
            x = random.randint(WINDOW_SIZE // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                             WINDOW_SIZE // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
            y = random.randint(WINDOW_SIZE // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                             WINDOW_SIZE // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
            ball = Ball(x, y)
            if is_inside_heptagon(ball.pos, heptagon):
                balls.append(ball)
                break
    
    # 游戏状态
    running = True
    paused = False
    show_fps = True
    font = pygame.font.Font(None, 36)
    
    # 主循环
    while running:
        dt = clock.tick(FPS) / 1000.0  # 转换为秒
        
        # 事件处理
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
                    for ball in balls:
                        while True:
                            x = random.randint(WINDOW_SIZE // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                                             WINDOW_SIZE // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
                            y = random.randint(WINDOW_SIZE // 2 - HEPTAGON_RADIUS + BALL_RADIUS,
                                             WINDOW_SIZE // 2 + HEPTAGON_RADIUS - BALL_RADIUS)
                            ball.pos = np.array([x, y], dtype=float)
                            if is_inside_heptagon(ball.pos, heptagon):
                                ball.vel = np.array([random.uniform(-5, 5), 
                                                   random.uniform(-5, 5)], dtype=float)
                                ball.trail.clear()
                                break
                elif event.key == pygame.K_f:
                    show_fps = not show_fps
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 点击添加新球
                mouse_pos = np.array(pygame.mouse.get_pos(), dtype=float)
                if is_inside_heptagon(mouse_pos, heptagon):
                    new_ball = Ball(mouse_pos[0], mouse_pos[1])
                    balls.append(new_ball)
        
        if not paused:
            # 更新七边形旋转
            heptagon.rotate(dt)
            
            # 更新球体
            for ball in balls:
                ball.update()
            
            # 碰撞检测
            edges = heptagon.get_edges()
            for ball in balls:
                # 球与边的碰撞
                for edge in edges:
                    ball_edge_collision(ball, edge)
                
                # 球与球的碰撞
                for other_ball in balls:
                    if ball != other_ball:
                        ball_ball_collision(ball, other_ball)
        
        # 绘制
        screen.fill(BACKGROUND_COLOR)
        
        # 绘制七边形
        heptagon.draw(screen)
        
        # 绘制球体
        for ball in balls:
            ball.draw(screen)
        
        # 显示FPS
        if show_fps:
            fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
            screen.blit(fps_text, (10, 10))
        
        # 显示控制说明
        controls = [
            "Space: 暂停/继续",
            "R: 重置球位置", 
            "ESC: 退出",
            "F: 显示/隐藏FPS",
            "鼠标点击: 添加新球"
        ]
        y_offset = 50
        small_font = pygame.font.Font(None, 20)
        for control in controls:
            text = small_font.render(control, True, (200, 200, 200))
            screen.blit(text, (10, y_offset))
            y_offset += 25
        
        # 显示球数量
        ball_count_text = font.render(f"Balls: {len(balls)}", True, (0, 255, 0))
        screen.blit(ball_count_text, (WINDOW_SIZE - 150, 10))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()