import pygame
import math
import random
import sys
from typing import List, Tuple
import time

# 初始化Pygame
pygame.init()

# 常量定义
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
WINDOW_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

# 七边形参数
HEPTAGON_RADIUS = 300
HEPTAGON_ROTATION_SPEED = 15  # 度/秒

# 球的参数
BALL_COUNT = 20
BALL_RADIUS = 8
GRAVITY = 9.81 * 50  # 调整重力强度以适应像素单位
ELASTICITY = 0.85  # 弹性系数

# 渲染参数
FPS = 60
BACKGROUND_COLOR = (0, 0, 0)
HEPTAGON_COLOR = (255, 255, 255)
TRAIL_LENGTH = 100  # 轨迹长度

class Vector2:
    """二维向量类，用于位置和速度计算"""
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar):
        return Vector2(self.x / scalar, self.y / scalar)
    
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def normalize(self):
        length = self.length()
        if length > 0:
            return Vector2(self.x / length, self.y / length)
        return Vector2(0, 0)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    
    def to_tuple(self):
        return (int(self.x), int(self.y))

class Ball:
    """球类，包含物理属性和渲染信息"""
    def __init__(self, x: float, y: float):
        self.position = Vector2(x, y)
        self.velocity = Vector2(
            random.uniform(-200, 200),  # 随机初始速度
            random.uniform(-200, 200)
        )
        self.radius = BALL_RADIUS
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        self.rotation = 0  # 自旋角度
        self.angular_velocity = random.uniform(-5, 5)  # 自旋速度
        self.trail = []  # 轨迹记录
    
    def update(self, dt: float):
        """更新球的位置和状态"""
        # 应用重力
        self.velocity.y += GRAVITY * dt
        
        # 更新位置
        self.position += self.velocity * dt
        
        # 更新自旋
        self.rotation += self.angular_velocity * dt
        
        # 记录轨迹
        self.trail.append((self.position.x, self.position.y))
        if len(self.trail) > TRAIL_LENGTH:
            self.trail.pop(0)
    
    def draw(self, screen):
        """绘制球和轨迹"""
        # 绘制轨迹
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = i / len(self.trail)
                trail_color = tuple(int(c * alpha * 0.3) for c in self.color)
                if i < len(self.trail):
                    try:
                        pygame.draw.line(screen, trail_color, 
                                       (int(self.trail[i-1][0]), int(self.trail[i-1][1])),
                                       (int(self.trail[i][0]), int(self.trail[i][1])), 2)
                    except:
                        pass
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, self.position.to_tuple(), self.radius)
        
        # 绘制自旋指示线
        end_x = self.position.x + self.radius * 0.7 * math.cos(self.rotation)
        end_y = self.position.y + self.radius * 0.7 * math.sin(self.rotation)
        pygame.draw.line(screen, (255, 255, 255), 
                        self.position.to_tuple(), (int(end_x), int(end_y)), 2)

class Heptagon:
    """正七边形容器类"""
    def __init__(self, center: Vector2, radius: float):
        self.center = center
        self.radius = radius
        self.rotation = 0
        self.vertices = []
        self.edges = []
        self._calculate_vertices()
    
    def _calculate_vertices(self):
        """计算七边形的顶点"""
        self.vertices = []
        for i in range(7):
            angle = self.rotation + i * 2 * math.pi / 7 - math.pi / 2
            x = self.center.x + self.radius * math.cos(angle)
            y = self.center.y + self.radius * math.sin(angle)
            self.vertices.append(Vector2(x, y))
        
        # 计算边
        self.edges = []
        for i in range(7):
            start = self.vertices[i]
            end = self.vertices[(i + 1) % 7]
            self.edges.append((start, end))
    
    def update(self, dt: float):
        """更新七边形旋转"""
        self.rotation += math.radians(HEPTAGON_ROTATION_SPEED) * dt
        self._calculate_vertices()
    
    def draw(self, screen):
        """绘制七边形"""
        if len(self.vertices) >= 3:
            points = [v.to_tuple() for v in self.vertices]
            pygame.draw.polygon(screen, HEPTAGON_COLOR, points, 3)
    
    def check_collision(self, ball: Ball) -> Tuple[bool, Vector2]:
        """检查球与七边形的碰撞，返回(是否碰撞, 法向量)"""
        for start, end in self.edges:
            # 计算点到线段的最短距离
            line_vec = end - start
            ball_vec = ball.position - start
            
            # 投影到线段上
            line_length_sq = line_vec.x ** 2 + line_vec.y ** 2
            if line_length_sq == 0:
                continue
                
            t = max(0, min(1, ball_vec.dot(line_vec) / line_length_sq))
            projection = start + line_vec * t
            
            # 计算距离
            distance_vec = ball.position - projection
            distance = distance_vec.length()
            
            if distance <= ball.radius:
                # 碰撞发生，计算法向量
                if distance > 0:
                    normal = distance_vec.normalize()
                else:
                    # 如果球心在线段上，使用垂直于线段的向量
                    normal = Vector2(-line_vec.y, line_vec.x).normalize()
                
                return True, normal
        
        return False, Vector2()

class PhysicsSimulator:
    """物理模拟引擎"""
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("旋转七边形弹跳球模拟器")
        self.clock = pygame.time.Clock()
        
        # 创建七边形容器
        self.heptagon = Heptagon(Vector2(*WINDOW_CENTER), HEPTAGON_RADIUS)
        
        # 创建球
        self.balls = []
        self._generate_balls()
        
        # 状态控制
        self.paused = False
        self.show_fps = True
        
        # 字体
        self.font = pygame.font.Font(None, 36)
        
    def _generate_balls(self):
        """生成随机分布的球"""
        self.balls = []
        for _ in range(BALL_COUNT):
            # 在七边形内生成随机位置
            while True:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, HEPTAGON_RADIUS - BALL_RADIUS - 50)
                x = WINDOW_CENTER[0] + distance * math.cos(angle)
                y = WINDOW_CENTER[1] + distance * math.sin(angle)
                
                # 检查是否在七边形内且不与其他球重叠
                valid = True
                for ball in self.balls:
                    if (Vector2(x, y) - ball.position).length() < BALL_RADIUS * 2:
                        valid = False
                        break
                
                if valid:
                    self.balls.append(Ball(x, y))
                    break
    
    def _handle_ball_collisions(self):
        """处理球与球之间的碰撞"""
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                ball1, ball2 = self.balls[i], self.balls[j]
                
                # 计算距离
                distance_vec = ball2.position - ball1.position
                distance = distance_vec.length()
                
                if distance < ball1.radius + ball2.radius and distance > 0:
                    # 碰撞发生，计算新速度
                    normal = distance_vec.normalize()
                    
                    # 分离球体
                    overlap = ball1.radius + ball2.radius - distance
                    separation = normal * (overlap / 2)
                    ball1.position -= separation
                    ball2.position += separation
                    
                    # 计算碰撞响应（弹性碰撞）
                    v1_normal = ball1.velocity.dot(normal)
                    v2_normal = ball2.velocity.dot(normal)
                    
                    # 新的法向分量（假设质量相等）
                    new_v1_normal = v2_normal * ELASTICITY
                    new_v2_normal = v1_normal * ELASTICITY
                    
                    # 更新速度
                    ball1.velocity += normal * (new_v1_normal - v1_normal)
                    ball2.velocity += normal * (new_v2_normal - v2_normal)
                    
                    # 更新自旋（碰撞时自旋方向改变）
                    ball1.angular_velocity *= -0.5
                    ball2.angular_velocity *= -0.5
    
    def _handle_boundary_collisions(self):
        """处理球与七边形边界的碰撞"""
        for ball in self.balls:
            collision, normal = self.heptagon.check_collision(ball)
            
            if collision:
                # 计算反射速度
                velocity_normal = ball.velocity.dot(normal)
                if velocity_normal < 0:  # 只有接近边界时才反弹
                    ball.velocity -= normal * (2 * velocity_normal)
                    ball.velocity *= ELASTICITY
                    
                    # 调整自旋
                    ball.angular_velocity += random.uniform(-2, 2)
    
    def _handle_events(self):
        """处理用户输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self._generate_balls()
                elif event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_f:
                    self.show_fps = not self.show_fps
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击添加球
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    new_ball = Ball(mouse_x, mouse_y)
                    self.balls.append(new_ball)
        
        return True
    
    def _draw_ui(self):
        """绘制用户界面信息"""
        y_offset = 10
        
        if self.show_fps:
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (255, 255, 255))
            self.screen.blit(fps_text, (10, y_offset))
            y_offset += 30
        
        ball_count_text = self.font.render(f"球数: {len(self.balls)}", True, (255, 255, 255))
        self.screen.blit(ball_count_text, (10, y_offset))
        y_offset += 30
        
        if self.paused:
            pause_text = self.font.render("已暂停 - 按空格继续", True, (255, 255, 0))
            self.screen.blit(pause_text, (10, y_offset))
            y_offset += 30
        
        # 控制说明
        instructions = [
            "空格: 暂停/继续",
            "R: 重置球",
            "F: 显示/隐藏FPS",
            "鼠标: 添加球",
            "ESC: 退出"
        ]
        
        small_font = pygame.font.Font(None, 24)
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (WINDOW_WIDTH - 150, 10 + i * 25))
    
    def run(self):
        """主运行循环"""
        running = True
        
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # 转换为秒
            
            # 处理事件
            running = self._handle_events()
            
            # 更新物理（如果未暂停）
            if not self.paused:
                # 更新七边形旋转
                self.heptagon.update(dt)
                
                # 更新球的物理
                for ball in self.balls:
                    ball.update(dt)
                
                # 处理碰撞
                self._handle_boundary_collisions()
                self._handle_ball_collisions()
            
            # 渲染
            self.screen.fill(BACKGROUND_COLOR)
            
            # 绘制七边形
            self.heptagon.draw(self.screen)
            
            # 绘制球
            for ball in self.balls:
                ball.draw(self.screen)
            
            # 绘制UI
            self._draw_ui()
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

def main():
    """主函数"""
    print("旋转七边形弹跳球模拟器")
    print("=" * 40)
    print("控制说明:")
    print("空格键: 暂停/继续模拟")
    print("R键: 重置所有球到随机位置")
    print("F键: 显示/隐藏FPS")
    print("鼠标左键: 在点击位置添加新球")
    print("ESC键: 退出程序")
    print("=" * 40)
    
    try:
        simulator = PhysicsSimulator()
        simulator.run()
    except Exception as e:
        print(f"程序运行出错: {e}")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()