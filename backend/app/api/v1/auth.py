@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        user_data (UserCreate): User registration details including email,
            password, full name, and company name.
        db (Session): Database session dependency.

    Returns:
        UserResponse: Newly created user information.

    Raises:
        HTTPException: If the email is already registered.
    """

    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company_name=user_data.company_name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and generate an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): Login credentials containing
            username and password.
        db (Session): Database session dependency.

    Returns:
        Token: JWT access token and token type.

    Raises:
        HTTPException: If credentials are invalid or user is inactive.
    """

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the authenticated user's profile information.

    Args:
        current_user (User): Authenticated user dependency.

    Returns:
        UserResponse: Current authenticated user details.
    """

    return current_user


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's password.

    Args:
        payload (ChangePasswordRequest): Current and new password data.
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        dict: Success message after password update.

    Raises:
        HTTPException: If current password is incorrect.
    """

    if not verify_password(
        payload.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(
        payload.new_password
    )

    current_user = db.merge(current_user)
    db.commit()

    return {
        "message": "Password updated successfully",
    }


@users_router.patch("/me", response_model=UserResponse)
def update_current_user_info(
    user_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's profile information.

    Args:
        user_data (UserUpdateSchema): Updated user profile data.
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        UserResponse: Updated user information.
    """

    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name

    if user_data.company_name is not None:
        current_user.company_name = user_data.company_name

    current_user = db.merge(current_user)

    db.commit()
    db.refresh(current_user)

    return current_user


@users_router.get("/me/stats", response_model=UserStatsResponse)
def get_current_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve statistics summary for the authenticated user.

    Args:
        current_user (User): Authenticated user dependency.
        db (Session): Database session dependency.

    Returns:
        UserStatsResponse: Summary of systems, documents,
        compliance status, and risk breakdown.
    """

    systems = (
        db.query(AISystem)
        .filter(AISystem.owner_id == current_user.id)
        .all()
    )

    risk_breakdown: dict = {}
    compliant_systems = 0

    for system in systems:
        if system.risk_level:
            key = system.risk_level.value
            risk_breakdown[key] = risk_breakdown.get(key, 0) + 1

        if system.compliance_status == ComplianceStatus.COMPLIANT:
            compliant_systems += 1

    total_documents = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .count()
    )

    return UserStatsResponse(
        total_systems=len(systems),
        total_documents=total_documents,
        risk_breakdown=risk_breakdown,
        compliant_systems=compliant_systems,
    )