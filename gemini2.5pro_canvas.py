import pygame
import math
import random
from collections import deque

# --- 1. 常量定义 (Constants Definition) ---
# 技术规格
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
BALL_COUNT = 20
FPS = 60
ROTATION_SPEED_DPS = 15  # Degrees per second

# 物理模拟参数
GRAVITY = 9.81 * 100  # 重力加速度 (g = 9.81 m/s^2, 假设 1m = 100 pixels)
ELASTICITY = 0.85  # 弹性系数 (球与墙)
BALL_ELASTICITY = 0.95 # 球与球之间的弹性

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# --- 2. 核心类定义 (Core Classes Definition) ---

class Ball:
    """
    定义球体对象，包含物理属性和行为
    Defines the Ball object, including its physical properties and behaviors.
    """
    def __init__(self, container_center):
        self.radius = BALL_RADIUS
        # 在容器中心附近随机生成，避免初始时卡在边界外
        # Spawn near the container center to avoid starting outside the boundary.
        self.position = pygame.math.Vector2(
            container_center.x + random.uniform(-50, 50),
            container_center.y + random.uniform(-50, 50)
        )
        self.velocity = pygame.math.Vector2(
            random.uniform(-200, 200),
            random.uniform(-200, 200)
        )
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.mass = self.radius ** 2
        # 附加挑战：轨迹跟踪
        # Bonus Challenge: Trail tracking
        self.trail = deque(maxlen=100)

    def update(self, dt):
        """
        更新球的位置和速度
        Update ball's position and velocity.
        """
        # 应用重力
        # Apply gravity
        self.velocity.y += GRAVITY * dt
        self.position += self.velocity * dt
        
        # 更新轨迹
        # Update trail
        self.trail.append(self.position.copy())

    def draw(self, screen):
        """
        在屏幕上绘制球体
        Draw the ball on the screen.
        """
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)

    def draw_trail(self, screen):
        """
        绘制球的轨迹
        Draw the ball's trail.
        """
        if len(self.trail) > 2:
            # 创建一个颜色稍暗的轨迹
            # Create a slightly darker trail color
            trail_color = tuple(max(0, c - 100) for c in self.color)
            pygame.draw.aalines(screen, trail_color, False, list(self.trail))

class Heptagon:
    """
    定义旋转的七边形容器
    Defines the rotating heptagon container.
    """
    def __init__(self, center, radius):
        self.center = pygame.math.Vector2(center)
        self.radius = radius
        self.angle = 0  # 当前旋转角度 (弧度)
        self.angular_velocity = math.radians(ROTATION_SPEED_DPS)  # 弧度/秒
        self.num_sides = 7
        self.vertices = []
        self.update(0) # 初始化顶点

    def update(self, dt):
        """
        更新七边形的旋转角度
        Update the heptagon's rotation angle.
        """
        # 顺时针旋转 (在pygame坐标系中，角度增加是逆时针，所以用减法)
        # Clockwise rotation (in pygame coordinates, increasing angle is counter-clockwise, so we subtract)
        self.angle -= self.angular_velocity * dt
        self.vertices = self._calculate_vertices()

    def _calculate_vertices(self):
        """
        根据当前角度计算顶点坐标
        Calculate vertex coordinates based on the current angle.
        """
        points = []
        for i in range(self.num_sides):
            angle_rad = 2 * math.pi * i / self.num_sides + self.angle
            x = self.center.x + self.radius * math.cos(angle_rad)
            y = self.center.y + self.radius * math.sin(angle_rad)
            points.append(pygame.math.Vector2(x, y))
        return points

    def get_walls(self):
        """
        获取构成七边形的墙体（线段）
        Get the wall segments that form the heptagon.
        """
        walls = []
        for i in range(self.num_sides):
            p1 = self.vertices[i]
            p2 = self.vertices[(i + 1) % self.num_sides]
            walls.append((p1, p2))
        return walls

    def draw(self, screen):
        """
        在屏幕上绘制七边形
        Draw the heptagon on the screen.
        """
        pygame.draw.polygon(screen, WHITE, self.vertices, 2)

    def is_inside(self, point):
        """
        判断一个点是否在七边形内部 (Winding Number Algorithm)
        Check if a point is inside the heptagon.
        """
        # 这是一个简单的点在多边形内的测试，对于凸多边形足够
        # This is a simple point-in-polygon test, sufficient for a convex polygon.
        for i in range(self.num_sides):
            p1 = self.vertices[i]
            p2 = self.vertices[(i + 1) % self.num_sides]
            # 计算叉积来判断点在边的哪一侧
            # Calculate cross product to determine which side of the edge the point is on.
            edge_vec = p2 - p1
            point_vec = point - p1
            if edge_vec.cross(point_vec) < 0:
                return False
        return True

class Simulation:
    """
    主模拟类，管理所有对象和游戏循环
    Main simulation class, manages all objects and the game loop.
    """
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bouncing Balls in Rotating Heptagon")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 30)
        self.running = True
        self.paused = False

        self.heptagon = Heptagon((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), HEPTAGON_RADIUS)
        self.balls = []
        self.reset()

    def reset(self):
        """
        重置模拟，重新生成所有球
        Reset the simulation, regenerating all balls.
        """
        self.balls = [Ball(self.heptagon.center) for _ in range(BALL_COUNT)]

    def run(self):
        """
        主游戏循环
        Main game loop.
        """
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            
            self.handle_events()
            if not self.paused:
                self.update(dt)
            self.draw()

        pygame.quit()

    def handle_events(self):
        """
        处理用户输入（键盘、鼠标、退出）
        Handle user input (keyboard, mouse, quit).
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                if event.key == pygame.K_r:
                    self.reset()
            # 附加挑战：鼠标点击添加新球
            # Bonus Challenge: Add new ball on mouse click
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    mouse_pos = pygame.math.Vector2(event.pos)
                    if self.heptagon.is_inside(mouse_pos):
                        new_ball = Ball(self.heptagon.center)
                        new_ball.position = mouse_pos
                        self.balls.append(new_ball)


    def update(self, dt):
        """
        更新所有游戏对象的状态
        Update the state of all game objects.
        """
        self.heptagon.update(dt)
        for ball in self.balls:
            ball.update(dt)
        
        self.handle_collisions()

    def handle_collisions(self):
        """
        处理所有类型的碰撞
        Handle all types of collisions.
        """
        # 球与墙的碰撞
        # Ball-wall collisions
        walls = self.heptagon.get_walls()
        for ball in self.balls:
            for p1, p2 in walls:
                self.collide_ball_with_wall(ball, p1, p2)

        # 球与球的碰撞
        # Ball-ball collisions
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                ball1 = self.balls[i]
                ball2 = self.balls[j]
                self.collide_balls(ball1, ball2)

    def collide_ball_with_wall(self, ball, p1, p2):
        """
        处理单个球与单面墙的碰撞检测和响应
        Handle collision detection and response for a single ball and a single wall.
        """
        wall_vec = p2 - p1
        point_vec = ball.position - p1
        
        # 投影长度 t = (ball - p1) · (p2 - p1) / |p2 - p1|^2
        # Projection length t = (ball - p1) dot (p2 - p1) / |p2 - p1|^2
        t = point_vec.dot(wall_vec) / wall_vec.length_squared()
        
        # 限制 t 在 [0, 1] 之间，找到墙上最近的点
        # Clamp t between 0 and 1 to find the closest point on the wall segment
        t = max(0, min(1, t))
        closest_point = p1 + t * wall_vec
        
        dist_vec = ball.position - closest_point
        distance = dist_vec.length()

        if distance < ball.radius:
            # --- 碰撞响应 (Collision Response) ---
            
            # 1. 位置校正 (Positional Correction)
            # 将球移出墙体，避免卡住
            # Move the ball out of the wall to prevent sticking.
            overlap = ball.radius - distance
            ball.position += dist_vec.normalize() * overlap
            
            # 2. 速度反射 (Velocity Reflection)
            # 计算墙的法线向量 (向外)
            # Calculate the wall's normal vector (pointing outwards).
            normal = wall_vec.rotate(90).normalize()
            if normal.dot(self.heptagon.center - p1) > 0:
                normal = -normal # 确保法线指向容器外部 Ensure normal points out of the container

            # 速度在法线方向上的分量
            # Velocity component along the normal
            v_normal_component = ball.velocity.dot(normal)
            
            # 只有当球正在向墙内运动时才进行反射
            # Only reflect if the ball is moving into the wall
            if v_normal_component < 0:
                # 反射速度: v_new = v - (1 + e) * (v · n) * n
                # Reflected velocity: v_new = v - (1 + e) * (v dot n) * n
                ball.velocity -= (1 + ELASTICITY) * v_normal_component * normal

    def collide_balls(self, ball1, ball2):
        """
        处理两个球之间的碰撞
        Handle collision between two balls.
        """
        dist_vec = ball2.position - ball1.position
        distance = dist_vec.length()
        
        if distance < ball1.radius + ball2.radius:
            # --- 碰撞响应 (Collision Response) ---
            
            # 1. 位置校正 (Positional Correction)
            overlap = (ball1.radius + ball2.radius) - distance
            correction = dist_vec.normalize() * overlap / 2
            ball1.position -= correction
            ball2.position += correction
            
            # 2. 速度交换 (Velocity Exchange - 动量守恒)
            # Momentum conservation
            normal = dist_vec.normalize()
            tangent = pygame.math.Vector2(-normal.y, normal.x)
            
            # 将速度投影到法线和切线方向
            # Project velocities onto normal and tangent directions
            v1n = ball1.velocity.dot(normal)
            v1t = ball1.velocity.dot(tangent)
            v2n = ball2.velocity.dot(normal)
            v2t = ball2.velocity.dot(tangent)
            
            # 切线方向速度不变
            # Tangential velocities remain unchanged
            
            # 法线方向速度根据弹性碰撞公式计算 (m1=m2时，速度交换)
            # Normal velocities are calculated using elastic collision formulas (velocities swap if m1=m2)
            m1, m2 = ball1.mass, ball2.mass
            new_v1n = (v1n * (m1 - m2) + 2 * m2 * v2n) / (m1 + m2)
            new_v2n = (v2n * (m2 - m1) + 2 * m1 * v1n) / (m1 + m2)
            
            # 乘以弹性系数
            new_v1n *= BALL_ELASTICITY
            new_v2n *= BALL_ELASTICITY

            # 将新的法线速度与旧的切线速度组合成最终速度
            # Combine new normal velocity with old tangential velocity for the final velocity
            ball1.velocity = new_v1n * normal + v1t * tangent
            ball2.velocity = new_v2n * normal + v2t * tangent

    def draw(self):
        """
        绘制所有游戏元素
        Draw all game elements.
        """
        self.screen.fill(BLACK)
        
        # 绘制轨迹 (在球下方)
        # Draw trails (underneath the balls)
        for ball in self.balls:
            ball.draw_trail(self.screen)

        self.heptagon.draw(self.screen)
        
        for ball in self.balls:
            ball.draw(self.screen)
            
        # 绘制UI信息
        # Draw UI information
        self.draw_ui()
        
        pygame.display.flip()

    def draw_ui(self):
        """
        绘制FPS、暂停状态等UI信息
        Draw UI info like FPS, paused state, etc.
        """
        # FPS 显示
        fps_text = self.font.render(f"FPS: {self.clock.get_fps():.1f}", True, GREEN)
        self.screen.blit(fps_text, (10, 10))
        
        # 球数量显示
        ball_count_text = self.font.render(f"Balls: {len(self.balls)}", True, WHITE)
        self.screen.blit(ball_count_text, (10, 40))

        # 暂停提示
        if self.paused:
            paused_text = self.font.render("PAUSED", True, RED)
            text_rect = paused_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(paused_text, text_rect)
            
        # 操作说明
        controls_text = self.font.render("SPACE: Pause | R: Reset | ESC: Quit | Click: Add Ball", True, WHITE)
        controls_rect = controls_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 20))
        self.screen.blit(controls_text, controls_rect)


# --- 3. 主程序入口 (Main Program Entry Point) ---
if __name__ == '__main__':
    sim = Simulation()
    sim.run()

