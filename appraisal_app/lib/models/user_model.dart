class UserModel {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String fullName;
  final String staffId;
  final String role;
  final String designation;
  final String phone;
  final int? department;
  final String? departmentName;
  final int? supervisor;
  final String? supervisorName;
  final String? profilePictureUrl;

  UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.staffId,
    required this.role,
    required this.designation,
    required this.phone,
    this.department,
    this.departmentName,
    this.supervisor,
    this.supervisorName,
    this.profilePictureUrl,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] ?? 0,
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      firstName: json['first_name'] ?? '',
      lastName: json['last_name'] ?? '',
      fullName: json['full_name'] ?? '',
      staffId: json['staff_id'] ?? '',
      role: json['role'] ?? 'STAFF',
      designation: json['designation'] ?? '',
      phone: json['phone'] ?? '',
      department: json['department'],
      departmentName: json['department_name'],
      supervisor: json['supervisor'],
      supervisorName: json['supervisor_name'],
      profilePictureUrl: json['profile_picture_url'] ?? json['profile_picture'],
    );
  }

  bool get isStaff => role == 'STAFF';
  bool get isSupervisor => role == 'SUPERVISOR';
  bool get isHod => role == 'HOD';
  bool get isDirectorate => role == 'DIRECTORATE';
  bool get isHrAdmin => role == 'HR_ADMIN';
  bool get isReviewer => isSupervisor || isHod || isDirectorate || isHrAdmin;
}
